import socket

LISTEN_HOST = '127.0.0.1'
LISTEN_PORT = 27777

# Create a TCP stream client socket for client-proxy communication
def start_proxy():
    proxy_socket = None
    try:
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)      # allow port reuse
        proxy_socket.bind((LISTEN_HOST, LISTEN_PORT))
        proxy_socket.listen(10)
        print("======================")
        print(f"Proxy server started, listen {LISTEN_HOST}:{LISTEN_PORT}...")

        while True:
            client_socket, address = proxy_socket.accept()      # create client socket, receive client request & foward server resopnse
            print("======================")
            print(f"Receive from {address} request")
            proxy_server_part(client_socket)    # called server part in proxy

    except KeyboardInterrupt:       # When user enter ctrl+c, means close the proxy server
        print("\nClosing the proxy server...")
    finally:
        proxy_socket.close()

# server side in proxy: 
# receive request from client, receive response from proxy-client-side
# forward client request to proxy-client-side
# modify the response from proxy-client-side
# forward the modified response to client
def proxy_server_part(client_socket:socket):    
    try:
        client_socket.settimeout(50)    # set timeout
        request_data = client_socket.recv(5000)
        if not request_data:
            print("No request from client")
            client_socket.close()
            return
        request_text = request_data.decode('utf-8',errors = 'ignore')
        print("======================")
        print(f"Receive HTTP request from client:\n{request_text}")
        response_data = proxy_client_part(request_text, client_socket)     # Forward request to proxy client part
        modified_data = modify_response(response_data)                     # Modified the data
        if modified_data:                                                  # Forward response to client
            client_socket.sendall(modified_data)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

# client side in proxy:
# receive request from proxy-server-side, receive response from web-server
# analysis request, forward to web-server
# create server socket for proxy-web server communication
# forward response to proxy-server-side
def proxy_client_part(request_text,client_socket):
    try:
        request_total_lines = request_text.split('\r\n')    # Analysis the HTTP request
        request_line = request_total_lines[0]
        print("======================")
        print(f"The client request first line is: {request_line}")
        try:
            method, request_url, version = request_line.split(' ', 2)      # Analysis the request line
        except ValueError:
            print("Requset format error")
            return None
        if method != "GET":
            return None

        if request_url.startswith('http://'):       # Get the web-server host and port
            url = request_url[7:]
            if '/' in url:
                host, path = url.split('/', 1)
                path = "/" + path
            else:
                host = url
                path = "/"

            if ':' in host:
                server_host, server_strport = host.split(':')
                server_port = int(server_strport)
            else:
                server_host = host
                server_port = 80
        else:
            for line in request_total_lines:
                if line.lower().startswith('host:'):
                    host = line[5:].strip()
                    if ":" in host:
                        server_host, server_strport = host.split(':')
                        server_port = int(server_strport)
                    else:
                        server_host = host
                        server_port = 80
                    break
        print("======================")
        print(f"Proxy analysis the web server is: {server_host} : {server_port}")
        
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)       # create server socket
        server_socket.connect((server_host, server_port))                       # connect to web-server
        server_socket.sendall(request_text.encode('utf-8'))
       
        response_data = b''
        while True:
            data = server_socket.recv(5000)
            if not data:
                break
            response_data += data
        print("======================")
        print(f"The web server response data successed")
        server_socket.close()
        return response_data
    
    except Exception as e:
        print("Error: {e}")
        return

def header_body_separator(response_data:bytes):
    separator = b'\r\n\r\n'
    if separator in response_data:
        header, body = response_data.split(separator, 1)
        return header, body
    else:
        print("Response not include body")
        return response_data, b''

# analysis the content type, only modify the text type
def extract_modify_content_type(response_data:bytes):
    header, body = header_body_separator(response_data)
    header_text = header.decode('utf-8').split('\r\n')          # check the content type
    for line in header_text:
        if line.lower().startswith('content-type:'):
            type = line.split(':', 1)[1].strip()
            content_type = type.split(';', 1)[0].strip()
            process_type = ['text/html',
                            'text/plain',
                            'text/css',
                            'text/javascript',
                            'application/json',
                            'application/xml',
                            'application/javascript']
            if content_type in process_type:
                return True
            else:
                return False

# update header length and reorganize header
def update_header_length(header:bytes, new_length:int):
    header_text = header.decode('utf-8').split('\r\n')          # check the content type
    update_line = []
    for line in header_text:
        if line.lower().startswith('content-length:'):
            update_line.append(f'Content-Length: {new_length}')
        else:
            update_line.append(line)
    return '\r\n'.join(update_line).encode('utf-8')

# extract status code, deal with diffrent situation, only modify text when code is 200 
def extract_status_code(header:bytes):
    header_text = header.decode('utf-8').split('\r\n')
    version, code, phrase = header_text[0].split(' ', 2)
    return int(code)

# analysis the resonpse body text, modify text
def modify_response(response_data:bytes):
    header, body = header_body_separator(response_data)
    code = extract_status_code(header)
    if code == 200:
        if extract_modify_content_type(response_data):
            body_text = body.decode('utf-8')
            print(f"Orignal body length is: {len(body_text)}")

            if "Stockholm" in body_text:
                print("======================")
                print("Found 'Stockholm', replacing with 'Linköping'")
                body_text = body_text.replace("Stockholm", "Linköping")
                if "/Linköping-spring.jpg" in body_text:                # deal with right stockholm url
                    body_text = body_text.replace("/Linköping-spring.jpg", "/Stockholm-spring.jpg")
                if "/smiley.jpg" in body_text:
                    print("Found smiley.jpg, replacing with trolly.jpg")
                    body_text = body_text.replace("/smiley.jpg", "/trolly.jpg")
            
                new_body = body_text.encode('utf-8')
                update_header = update_header_length(header, len(new_body))
                modified_data = update_header + b"\r\n\r\n" + new_body
                print(f"Modified body length is: {len(new_body)}")

                print("======================")
                print(f"The modified response header is:\n{update_header.decode('utf-8')}")
                return modified_data
            else:
                print("No content need to modify")
                return response_data
        else:
            print("No content type can be modified")
            return response_data
        
    if code == 304:
        print("======================")
        print("Processing 304 Not Modified: The content not changed, no need to modify")
        return response_data
    
    if code == 404:
        print("======================")
        print("Processing 404 not found")
        return response_data
    
if __name__ == "__main__":
    start_proxy()