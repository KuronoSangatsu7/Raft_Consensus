from concurrent import futures
import raft_pb2
import raft_pb2_grpc
import random
import sys
import time
import grpc

# Applies corresponding changes upon a term change event 
def invoke_term_change (term):
    global myLeaderId, votedId, timer, myState, myTerm

    if myState != "Follower" or term != myTerm:
        print(f"I am a follower. Term: {term}")

    timer = 0
    myTerm = term
    myLeaderId = -1
    votedId = -1
    myState = "Follower"

# Reads the list of servers from config.conf and saves the data to a global dictionary
def init_servers():
    global servers
    servers = {}

    with open("config.conf", "r") as f:
        for line in f:
            servers[int(line.split(" ")[0])] = f'{line.split(" ")[1]}:{line.split(" ")[2].rstrip()}'

# Initilizes global variables and copies over ID from command line arguments
def startup():
    global id, myTerm, timer, timerLimit, myState, votedId, servers, myLeaderId, suspended, globalPeriod, commitIndex, lastApplied, logs, myDict, nextIndex, matchIndex

    init_servers()

    id = int(sys.argv[1])
    suspended = False
    myDict = {}
    logs = []
    nextIndex = {}
    matchIndex = {}
    lastApplied = 0
    commitIndex = 0
    globalPeriod = 0
    myTerm = 0
    timer = 0
    timerLimit = random.randint(150, 300)
    myState = "Follower"
    votedId = -1
    myLeaderId = -1
    
    print(f"The server starts at {servers[id]}")
    print("I am a follower. Term: 0")

# Responds to a RequestVote request from a candidate
def request_vote(term, candidateId, lastLogIndex, lastLogTerm):
    global votedId, myTerm, myState, logs

    if term > myTerm:
        myTerm = term
        votedId = -1

        return request_vote(term, candidateId, lastLogIndex, lastLogTerm)

    # If term < term number on this server, then reply False or if this server already voted on this term, then reply False.
    if term < myTerm or votedId != -1:
        return (myTerm, False)

    #If lastLogIndex < last log index of the server, then reply False
    if lastLogIndex < len(logs):
        return (myTerm, False)

    #If there is lastLogIndex entry on this server, and its term is not equal to lastLogTerm, then reply False.
    if lastLogIndex != 0 and logs[lastLogIndex - 1]["term"] != lastLogTerm:
        return (myTerm, False)

    votedId = candidateId
    myState = "Follower"

    print(f"Voted for node {candidateId}")
    print(f"I am a follower. Term: {myTerm}")

    return (myTerm, True)

# Receives a heartbeat from the leader
def append_entries(term, leaderId, prevLogIndex, prevLogTerm, entries, leaderCommit):
    global myTerm, myState, timer, myLeaderId, logs, commitIndex


    timer = 0

    if myTerm > term:
        return (myTerm, False)

    if prevLogIndex > len(logs):
        return (myTerm, False)

    entriesIndex = 0
    logsIndex = prevLogIndex

    while logsIndex < len(logs) and entriesIndex < len(entries):
        if logs[logsIndex] != entries[entriesIndex]:
            logs = logs[0:logsIndex]
            break

        logsIndex += 1
        entriesIndex += 1

    logs += entries[entriesIndex:]

    if leaderCommit > commitIndex:
        commitIndex = min(leaderCommit, prevLogIndex + len(entries))
    
    if term > myTerm:
        invoke_term_change(term)
    myLeaderId = leaderId

    return (myTerm, True)

# Responds to a GetLeader request from the client
def get_leader():
    global myLeaderId, votedId, servers

    print("Command from client: getleader")

    if myLeaderId != -1:
        print(f"{myLeaderId} {servers[myLeaderId]}")
        return (myLeaderId, servers[myLeaderId])

    if votedId != -1:
        print(f"{votedId} {servers[votedId]}")
        return (votedId, servers[votedId])

    print("None")
    return ("None", "None")

# Executes a Suspend command issued by the client
def suspend(period):
    global suspended, globalPeriod

    print(f"Command from client: suspend {period}")
    print(f'Sleeping for {period} seconds')

    suspended = True
    globalPeriod = period

# Executes a SetVal command issued by the client
def set_val(key, value):
    global logs

    if myState == "Candidate":
        return False
    
    if myState == "Leader":
        newEntry = {"term" : myTerm, "command" : f"{key} {value}"}
        logs.append(newEntry)
        return True
    
    channel = grpc.insecure_channel(servers[myLeaderId])
    stub = raft_pb2_grpc.RaftServiceStub(channel)

    try:
        params = raft_pb2.SetValRequest(key=key, value=value)
        response = stub.SetVal(params)
    except grpc.RpcError:
        return False

    return response.verdict

# Executes a GetVal command issued by the client
def get_val(key):

    if key not in myDict:
        return (False, "None")
    
    return (True, myDict[key])

# Applies the necessary immediate changes upon turning into a leader.
def handle_leader_init():
    global myState, myLeaderId, nextIndex, matchIndex

    myState = "Leader"
    print(f"I am a leader. Term: {myTerm}")
    myLeaderId = id
    nextIndex = {}
    matchIndex = {}

    for key in servers:

        if key == id:
            continue
        
        nextIndex[key] = commitIndex + 1
        matchIndex[key] = 0


# Applies the necessary immediate changes upon turning into a candidate
# Sends RequestVote requests to other nodes, and decides whether or not to turn into the leader
def handle_candidate_init():
    global timer, id, myTerm, myState, votedId, myLeaderId

    print("The leader is dead")

    timer = 0
    
    invoke_term_change(myTerm + 1)
    
    myState = "Candidate"
    
    print(f"I am a candidate. Term: {myTerm}")
    
    vote_count = 1
    votedId = id
    
    print(f"Voted for node {id}")
    
    for key in servers:

        if key == id:
            continue
        try:
            address = servers[key]

            channel = grpc.insecure_channel(address)
            stub = raft_pb2_grpc.RaftServiceStub(channel)
            candidate = raft_pb2.TermCandIDPair(term=myTerm, candidateID=id)
            lastLogTerm = 0
            if len(logs) != 0:
                lastLogTerm = logs[-1]["term"]
            params = raft_pb2.RequestVoteRequest(candidate=candidate, lastLogIndex=len(logs), lastLogTerm=lastLogTerm)
            response = stub.RequestVote(params)

            term, result = response.result.term, response.result.verdict

        except grpc.RpcError:
            continue
        
        if term > myTerm:

            invoke_term_change(term)

            return

        vote_count += (result == True)

    print("Votes received")

    if (vote_count >= len(servers)/2 + 1):
        handle_leader_init()

# Handles the follower state
def handle_follower():
    global myState, timer, timerLimit

    if timer >= timerLimit:
        handle_candidate_init()

# Handles the candidate state
def handle_candidate():
    global timer, timerLimit, myState, logs

    if timer >= timerLimit:
        timerLimit = random.randint(150, 300)
        invoke_term_change(myTerm)

# Extracts a log entry from a ProtoBuf LogEntry message
def extract_log_entry_message(entry):
    return {'term' : entry.term, 'command' : entry.command}

# Forms a log entry into a ProtoBuf LogEntry message
def form_log_entry_message(entry):
    return raft_pb2.LogEntry(term=entry['term'], command=entry['command'])

# Handles the leader state
# Sends heartbeats every 50ms
def handle_leader():
    global timer, myTerm, id, commitIndex, nextIndex, matchIndex, logs

    if timer % 50 == 0:
        
        # Resets the timer to avoid overflowing in an infinite leader state
        # Applicable since the leader does not care about the timer limit
        timer = 0

        for key in servers:
            
            if key == id:
                continue

            while True:
                try:
                    # Sending an AppendEntries request

                    address = servers[key]
                    channel = grpc.insecure_channel(address)
                    stub = raft_pb2_grpc.RaftServiceStub(channel)
                    prevLogIndex = nextIndex[key] - 1
                    prevLogTerm = 0
                    if len(logs) != 0 and prevLogIndex != 0:
                        prevLogTerm = logs[prevLogIndex - 1]['term']
                    
                    paramEntries = [form_log_entry_message(x) for x in logs[prevLogIndex:]]
                    leader = raft_pb2.TermLeaderIDPair(term=myTerm, leaderID=id)
                    params = raft_pb2.AppendEntriesRequest(leader=leader, prevLogIndex=prevLogIndex, prevLogTerm=prevLogTerm, leaderCommit=commitIndex)
                    params.entries.extend(paramEntries)
                    response = stub.AppendEntries(params)

                    term, result = response.result.term, response.result.verdict
                        
                except grpc.RpcError:
                    break
                
                # If successful: update nextIndex and matchIndex for the follower.
                if result == True:
                    nextIndex[key] = matchIndex[key] = prevLogIndex + len(paramEntries) + 1
                    matchIndex[key] -= 1
                    nextIndex[key] = max(nextIndex[key], 1)
                    break
                
                # If, as a result of calling this function, the Leader receives a term number greater than its own term number
                # that Leader must update his term number and become a Follower
                if term > myTerm:
                    invoke_term_change(term)
                    return

                # If AppendEntries fails because of log inconsistency: decrement nextIndex and retry.
                nextIndex[key] -= 1
                if nextIndex[key] == 0:
                    nextIndex[key] = 1
                    break
    
        while commitIndex < len(logs):
            newCommitIndex = commitIndex + 1
            validServers = 1
            
            for key in matchIndex:
                if matchIndex[key] >= newCommitIndex:
                    validServers += 1

            if validServers >= len(servers)/2 + 1:
                commitIndex = newCommitIndex
            else:
                break

# If commitIndex > lastApplied: increment lastApplied and apply log[lastApplied] to state machine.
def apply_commits():
    global myDict, lastApplied

    while lastApplied < commitIndex:
        command = logs[lastApplied]['command'].split(' ')
        myDict[command[0]] = command[1]

        lastApplied += 1

# Terminates the server
def terminate():
    print(f"Server {id} is shutting down...")
    sys.exit(0)

# Handles current state
def handle_current_state():
    apply_commits()
    if myState == "Follower":
        handle_follower()
    if myState == "Candidate":
        handle_candidate()
    elif myState == "Leader":
        handle_leader()

# Initializes the server, and makes appropriate handle_current_state calls every 1ms
def main_loop():
    global timer, suspended

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    raft_pb2_grpc.add_RaftServiceServicer_to_server(RaftService(), server)
    server.add_insecure_port(servers[id])
    server.start()

    while True:

        if suspended:
            server.stop(0)
            time.sleep(globalPeriod)
            server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            raft_pb2_grpc.add_RaftServiceServicer_to_server(RaftService(), server)
            server.add_insecure_port(servers[id])
            server.start()
            suspended = False

        init_servers()
        handle_current_state()

        time.sleep(0.001)
        timer += 1


class RaftService(raft_pb2_grpc.RaftServiceServicer):
    def RequestVote(self, request, context):
        term = request.candidate.term
        candidate_id = request.candidate.candidateID
        last_log_index = request.lastLogIndex
        last_log_term = request.lastLogTerm

        voted = request_vote(term, candidate_id, last_log_index, last_log_term)

        result = raft_pb2.TermResultPair(term=voted[0], verdict=voted[1])

        response = raft_pb2.RequestVoteResponse(result=result)

        return response
    
    def AppendEntries(self, request, context):
        term = request.leader.term
        leader_id = request.leader.leaderID
        prev_log_index = request.prevLogIndex
        prev_log_term = request.prevLogTerm
        
        entries = []

        for entry in request.entries:
            entries.append(extract_log_entry_message(entry))

        leader_commit = request.leaderCommit

        appended = append_entries(term, leader_id, prev_log_index, prev_log_term, entries, leader_commit)

        result = raft_pb2.TermResultPair(term=appended[0], verdict=appended[1])

        response = raft_pb2.AppendEntriesResponse(result=result)

        return response

    def GetLeader(self, request, context):
        leader = get_leader()

        if leader[0] == "None":
            response = raft_pb2.GetLeaderResponse(nodeId=-1)
        
        else:
            response = raft_pb2.GetLeaderResponse(nodeId=leader[0], nodeAddress=leader[1])
        
        return response
    
    def Suspend(self, request, context):
        period = request.period

        suspend(period)

        return raft_pb2.Empty()
    
    def SetVal(self, request, context):
        key = request.key
        value = request.value

        set = set_val(key, value)
        response = raft_pb2.SetValResponse(verdict=set) 
        return response

    def GetVal(self, request, context):
        key = request.key

        get = get_val(key) 
        response = raft_pb2.GetValResponse(verdict=get[0], value=get[1])
        return response

def init():
    try:
        startup()
        main_loop()
    except KeyboardInterrupt:
        terminate()

init()