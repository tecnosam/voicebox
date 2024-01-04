import pyaudio


class Audio:

    CHUNK = 1024 * 20
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 50000

    pya = pyaudio.PyAudio()
    o_stream = pya.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

    @staticmethod
    def record(callback=None):

        p = pyaudio.PyAudio()
        stream = p.open(
            format=Audio.FORMAT,
            channels=Audio.CHANNELS,
            rate=Audio.RATE,
            input=True,
            frames_per_buffer=Audio.CHUNK,
            stream_callback=callback
        )

        return stream

    @staticmethod
    def play_audio(audio_stream):

        Audio.o_stream.write(audio_stream)

    @staticmethod
    def close_audio():
        Audio.o_stream.stop_stream()
        Audio.o_stream.close()
        Audio.pya.terminate()

