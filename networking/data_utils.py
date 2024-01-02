

class MessageStack:

    def __init__(self):
        self.__messages = []

    def add(self, msg):
        self.__messages.append(msg)

    def peek(self):
        return self.__messages[-1]

    def pop(self):
        if len(self.__messages) == 0:
            return ""

        return self.__messages.pop(-1)
