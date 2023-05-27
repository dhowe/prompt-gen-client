
import random
import config

from elevenlabs import generate, voices, play, stream, set_api_key

set_api_key(config.get_config_value('tts_api_key'))

class TextToSpeech:

    def __init__(self):
        # self.on = True
        # self.queue = queue.Queue()
        self.voices = list(voices())
        self.available_voices = self.voices.copy()
        self.last_voice = self.available_voices[0]
        self.voice_map = {}
        print('TextToSpeech loaded...')
        # print(self.voices[0])

    # def queue_utterance(self, utterance):
    #     self.queue.put(utterance)
    #     print(f'/tts-queued: {utterance}')


    # def stop(self):
    #     self.on = False
    #     print('TextToSpeech unloaded...')
    #
    # def start(self):
    #     self.on = True
    #     self.loop()
    #
    # def loop(self):
    #     print('TextToSpeech loaded...')
    #     while self.on:
    #         item = self.queue.get()
    #         self.speak(item['text'], speaker=item.get('speaker', None))
    #         time.sleep(.01)

    def speak(self, text, **kwargs):
        if len(text) and config.get_config_value("use_tts", True):
            speaker = kwargs.get('speaker', 'Narrator')
            use_stream = config.get_config_value('tts_streaming')
            if speaker and len(speaker):
                voice = self.voice_map.get(speaker, None)
                if not voice:
                    voice = self.get_available_voice()
                    self.voice_map[speaker] = voice
            else:
                voice = self.last_voice

                # print(self.name_voice_map())
            audio = generate(text=text, voice=voice, stream=use_stream)
            print(f'/tts {speaker}/{voice.name} -> \'{text}\'')
            if use_stream:
                stream(audio)
            else:
                play(audio)
            self.last_voice = voice

    def available_voice_names(self):
        return list(map(lambda v: v.name, self.available_voices))

    def name_voice_map(self):
        res = 'voice_map:\n'
        for char, voice in self.voice_map.items():
            res += f'  {char}: {voice.name}\n'
        return res

    def get_available_voice(self):
        """remove and return a random voice"""
        if len(self.available_voices) == 0:
            print('no voices remaining, choosing random...')
            self.available_voices = self.voices.copy()
        # print('Remaining:', self.available_voice_names())
        return self.available_voices.pop(random.randrange(len(self.available_voices)))

    def insert_pauses(self, text, spacer=' - '):
        """Inserts an equal number of spaces between words in the text."""
        words = text.split()
        spaced_text = (',' + spacer).join(words)
        print(spaced_text)
        return spaced_text
