### Raft Consensus
This is an implementation of the Raft consensus algorithm in Python. You can read more about the algorithm [here] (https://raft.github.io/raft.pdf) or opt for a visual representation of how it works [here](https://thesecretlivesofdata.com/raft/).

### Tech Used:
- `Python`
- `Protocol Buffers`
- `gRPC`

### Usage:

Install and activate the virtual environment then compile the `.proto` file using:
        
    pip install virtualenv

    virtualenv venv

    source venv/bin/activate

    pip install -r requirements.txt

    python3 -m grpc_tools.protoc raft.proto --proto_path=. --python_out=. --grpc_python_out=.

Then, create a `config.conf` file in the same directory with the desired server addresses and port numbers. An example of `config.conf` file:

        0 127.0.0.1 50000
        1 127.0.0.1 50001
        2 127.0.0.1 50002

The application consists of 2 main parts:

- Server - `server.py`:

    These are the main nodes that essentially implement the algorithm and go through the cycles of `Leader`, `Candidate`, `Follower` and perform operations such as `Leader Election` and `Log Replication`.

    The server nodes output simple updates of when they change their state (e.g. `leader` -> `follower`), make or receive `votes`, and answer queries received from the `client`.

    To run a `server node`, simply run an instance of `server.py` and pass the corresponding number associated with this server from `config.conf` file. Here are two examples of a server node's output: 

    Example 1:

        >python server.py 0
        The server starts at 127.0.0.1:50000
        I am a follower. Term: 0
        The leader is dead
        I am a candidate. Term: 1
        Voted for node 0
        Votes received
        I am a leader. Term: 1
        Command from client: getleader
        0 127.0.0.1:50000
    
    Example 2:

       >python server.py 0
        The server starts at 127.0.0.1:50000
        I am a follower. Term: 0
        The leader is dead
        I am a candidate. Term: 1
        Voted for node 0
        Votes received
        I am a leader. Term: 1
        Command from client: getleader
        0 127.0.0.1:50000
        Command from client: suspend 2
        Sleeping for 2 seconds
        I am a follower. Term: 2
        Command from client: getleader
        2 127.0.0.1:50002

- Client - `client.py`:

    Client nodes are essentially "users" of the system. They can perform the following operations:

    - `connect SERVER_ADDRESS SERVER_PORT_NUMBER`: Connects to the corresponding server node and issues all subsequent commands to that node until either the node dies or `connect` is called on another server node.

    - `getleader`: Sends a request to the currently connected server to identify the current leader of the raft and prints the output.

    - `setval KEY VAL`: Asks the currently connected server to save `VAL` to the distributed system under `KEY`.

    - `getval KEY`: Asks the currently connected server to return the currently saved `VAL` under `KEY` in the distributed system.

    - `suspend PERIOD`: Commands the currently connected server to `sleep` for `PERIOD` seconds, during which that server node basically exists the system and re-enters after `PERIOD` seconds.

    To run a `client node`, simply run an instance of `client.py` as such:

    Example 1: 

        >python client.py
        The client starts
        > connect 127.0.0.1 50001
        > getleader
        0 127.0.0.1:50000
        > getval key1
        None
        > setval key1 100
        > getval key1
        100

    Example 2:

        >python client.py
        The client starts
        >connect 127.0.0.1 50000
        >getleader
        0 127.0.0.1:50000
        >suspend 2
        >getleader
        2 127.0.0.1:50002
        >quit
        The client ends

### Author Contact Info:
    Jaffar Totanji
    Email: jaafarti@gmail.com
    Telegram: @KuroHata7

    Ahmad Haidar
    Email: togoyany@gmail.com
    Telegram: @XmtosX

##### P.S: This work was done as a solution to an assignment given to us as part of the Distributed and Network Programming course at IU.