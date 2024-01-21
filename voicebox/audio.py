
import pyaudio


class Audio:
    """
    Audio Class

    This class provides functionality for recording and playing audio using PyAudio.

    Attributes:
        CHUNK (int): The size of each audio chunk to be processed.
        FORMAT: The audio format used by PyAudio (paInt16 for 16-bit PCM).
        CHANNELS (int): The number of audio channels (1 for mono).
        RATE (int): The sampling rate of the audio.

    Example:
        # Create an Audio instance
        audio_instance = Audio()

        # Record audio with a callback
        def custom_callback(in_data, frame_count, time_info, status):
            # Custom audio processing logic here
            return None, pyaudio.paContinue

        audio_stream = audio_instance.record(callback=custom_callback)

        # Play the recorded audio
        audio_instance.play_audio(audio_stream)

        # Close the audio stream and terminate PyAudio
        audio_instance.close_audio()
    """

    CHUNK = 1024 * 5
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 50000

    pya = pyaudio.PyAudio()
    o_stream = pya.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        output=True
    )

    @staticmethod
    def record(callback=None):
        """
        Record audio using PyAudio.

        Args:
            callback (callable, optional): A callback function that will be invoked with audio
                data as it becomes available. If not provided, the audio data will be processed
                by the stream's `read` method.

        Returns:
            pyaudio.Stream: A PyAudio stream object representing the audio input stream.

        Example:
            # Usage without callback
            stream = Audio.record()

            # Usage with callback
            def custom_callback(in_data, frame_count, time_info, status):
                # Custom audio processing logic here
                return None, pyaudio.paContinue

            stream = Audio.record(callback=custom_callback)
        """
        pyaudio_object = pyaudio.PyAudio()
        stream = pyaudio_object.open(
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
        """
        Play audio using the provided PyAudio stream.

        Args:
            audio_stream (pyaudio.Stream): The PyAudio stream containing audio data to be played.
        """
        Audio.o_stream.write(audio_stream)

    @staticmethod
    def close_audio():
        """
        Close the audio output stream and terminate the PyAudio instance.
        """
        Audio.o_stream.stop_stream()
        Audio.o_stream.close()
        Audio.pya.terminate()
