import grpc
import raft_pb2
import raft_pb2_grpc
import sys

# The IP address and port number of the server to which commands will be issued
server_ip_addr_port_num = ""

# Print a message in case the current server is offline
def server_failure():
    print(f"The server {server_ip_addr_port_num} is unavailable")
    return

# Parse user input from command line
def parse_user_input(message):
    command = message.split(" ")[0]
    parsed_message = message.split(" ")

    if command == "connect":
        return ("Connect", parsed_message[1])
    elif command == "getleader":
        return ("GetLeader", "GetLeader")
    elif command == "suspend":
        return ("Suspend", int(parsed_message[1]))
    elif command == "setval":
        return ("SetVal", parsed_message[1], parsed_message[2])
    elif command == "getval":
        return ("GetVal", parsed_message[1])
    elif command == "quit":
        return ("Quit", "quit")
    else:
        return ("Invalid", "invalid")

# Set the global server variable to the provided one
def connect(ip_addr_port_num):

    global server_ip_addr_port_num

    server_ip_addr_port_num = ip_addr_port_num

# Issue a GetLeader command to the server
def get_leader():
    channel = grpc.insecure_channel(server_ip_addr_port_num)
    stub = raft_pb2_grpc.RaftServiceStub(channel)

    try:
        params = raft_pb2.Empty()
        response = stub.GetLeader(params)
    except grpc.RpcError:
        server_failure()
        return

    if response.nodeId == -1:
        print("No leader. This node hasn't voted for anyone in this term yet...")
    
    else:
        print(f"{response.nodeId} {response.nodeAddress}")

# Issue a Suspend command to the server
def suspend(period):
    channel = grpc.insecure_channel(server_ip_addr_port_num)
    stub = raft_pb2_grpc.RaftServiceStub(channel)

    try:
        params = raft_pb2.SuspendRequest(period=period)
        response = stub.Suspend(params)
    except grpc.RpcError:
            server_failure()
            return

# Issue a SetVal command to the server
def set_val(key, value):
    channel = grpc.insecure_channel(server_ip_addr_port_num)
    stub = raft_pb2_grpc.RaftServiceStub(channel)

    try:
        params = raft_pb2.SetValRequest(key=key, value=value)
        response = stub.SetVal(params)
    except grpc.RpcError:
            server_failure()
            return

# Issue a GetVal command to the server
def get_val(key):
    channel = grpc.insecure_channel(server_ip_addr_port_num)
    stub = raft_pb2_grpc.RaftServiceStub(channel)

    try:
        params = raft_pb2.GetValRequest(key=key)
        response = stub.GetVal(params)

        if response.verdict == False:
            print("None")
        else:
            print(response.value)
                    
    except grpc.RpcError:
            server_failure()
            return

# Terminate the client
def terminate():
    print("The client ends")
    sys.exit(0)

# Initialize the client
def init():
    print("The client starts")

    while True:
        try:
            user_input = input(">")
            parsed_input = parse_user_input(user_input)

            message_type = parsed_input[0]

            if message_type == "Connect":
                connect(parsed_input[1])
            elif message_type == "GetLeader":
                get_leader()
            elif message_type == "Suspend":
                suspend(parsed_input[1])
            elif message_type == "SetVal":
                set_val(parsed_input[1], parsed_input[2])
            elif message_type == "GetVal":
                get_val(parsed_input[1])
            elif message_type == "Quit":
                terminate()
            else:
                print("Invalid command! Please try again.")

        except KeyboardInterrupt:
            print("Use 'quit' to terminate the client program")

if __name__ == "__main__":
    init()