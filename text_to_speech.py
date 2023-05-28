import config
import random

from elevenlabs import generate, voices, play, stream, set_api_key

set_api_key(config.get_value('tts_api_key'))


class TextToSpeech:

    def __init__(self):
        self.debug = True
        self.voices = list(voices())
        self.available_voices = self.voices.copy()
        self.last_voice = self.available_voices[0]
        self.voice_map = {}
        if self.debug: print('Loading text-to-speech...')
        # print(self.voices[0])

    def speak(self, text, **kwargs):
        if len(text) and config.get_value("use_tts", True):
            speaker = kwargs.get('speaker', 'Narrator')
            use_stream = config.get_value('tts_streaming')
            stability = config.get_float('tts_stability', .75)
            similarity = config.get_float('tts_similarity', .75)
            # print('stability=', type(stability), stability, type(similarity), 'similarity=', similarity)
            if speaker and len(speaker):
                voice = self.voice_map.get(speaker, None)
                if not voice:
                    voice = self.get_available_voice()
                    self.voice_map[speaker] = voice
            else:
                voice = self.last_voice

            if voice.settings:
                voice.settings.stability = stability
                voice.settings.similarity_boost = similarity

            audio = generate(text=text, voice=voice, stream=use_stream)

            if self.debug: print(f'/tts \'{speaker}\'/\'{voice.name}\' -> '
                                 + f'\'{text}\' [sta={stability}, sim={similarity}]')

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
            if self.debug: print('all voices used, choosing random...')
            self.available_voices = self.voices.copy()
        # print('Remaining:', self.available_voice_names())
        return self.available_voices.pop(random.randrange(len(self.available_voices)))
