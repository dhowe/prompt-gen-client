import random

from elevenlabs import generate, voices, play, stream, set_api_key

import config

set_api_key(config.get_config_value('tts_api_key'))

class TextToSpeech:
    def __init__(self):
        self.voices = list(voices())
        self.available_voices = self.voices.copy()
        print(len(self.available_voices), "voices found")
        self.voice_map = {}
        # print(self.voices[0])

    def speak(self, text, **kwargs):
        if len(text) and config.get_config_value("use_tts", True):
            speaker = kwargs.get('speaker', 'Narrator')
            use_stream = kwargs.get('use_stream', False)
            voice = self.voice_map.get(speaker, None)
            if not voice:
                voice = self.get_available_voice()
                self.voice_map[speaker] = voice
                print(self.name_voice_map())
            audio = generate(text=text, voice=voice, stream=use_stream)
            if use_stream:
                stream(audio)
            else:
                play(audio)

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
        print('Remaining:', self.available_voice_names())
        return self.available_voices.pop(random.randrange(len(self.available_voices)))

    def insert_pauses(self, text, spacer=' - '):
        """Inserts an equal number of spaces between words in the text."""
        words = text.split()
        spaced_text = (',' + spacer).join(words)
        print(spaced_text)
        return spaced_text
