import socketserver

CRLF = "\r\n"
PORT = 61611


class CTP01Handler(socketserver.StreamRequestHandler):
    def write_command(self, *fields):
        command = "~".join(map(str, fields))
        print(">>", command)
        self.wfile.write((command + CRLF).encode())

    def read_command(self):
        command = self.rfile.readline().strip().decode()
        if command:
            print("<<", command)
        return command

    def handle(self):
        print("-- Client connected --")

        # Consume the greeting, do nothing with it
        greeting = self.read_command()

        # Respond with a greeting of our own, followed by some settings
        settings = ("location=multi", "guntimes=true", "newlocations=true", "authentication=none", "stream-mode=push", "time-format=iso")
        self.write_command("smserver", "0.0.1", len(settings))
        for setting in settings:
            self.write_command(setting)
        self.write_command("geteventinfo")
        self.write_command("getlocations")

        # Now, since we've put it into push mode, ask it to send everything
        self.write_command("start")

        # Finally just keep reading forever until it hangs up
        while True:
            command = self.read_command()
            if not command:
                break

        print("-- Client disconnected --")

if __name__ == "__main__":
    server = socketserver.ThreadingTCPServer(('', PORT), CTP01Handler)
    print(f"Server listening on port {PORT}")
    server.serve_forever()
