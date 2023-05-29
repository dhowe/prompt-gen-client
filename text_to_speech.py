import random

import gspread
from elevenlabs import generate, voices, play, stream, set_api_key

import config
from helpers import find

set_api_key(config.get_value('tts_api_key'))


class TextToSpeech:

    def __init__(self):
        self.debug = True
        self.voice_map = {}
        if self.debug: print('Loading text-to-speech...')
        self.voices = list(voices())
        self.available_voices = self.voices.copy()
        self.last_voice = self.available_voices[0]
        self.load_voice_map()

    def load_voice_map(self):
        sheet_id = config.get_value("character_voice_sheet_id")
        sheet_name = config.get_value("character_voice_sheet_name")
        gc = gspread.service_account('google_sheets_access.json')
        spreadsheet = gc.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        rows = worksheet.get_all_values()
        for i, row in enumerate(rows):
            if i < 2: continue
            char_name = row[0]
            voice_name = row[1]
            # reserved = row[2]
            voice = find(lambda v: v.name == voice_name, self.voices)
            self.voice_map[char_name] = voice
            self.available_voices.remove(voice)

        if self.debug:
            print('  Voice-mappings: {')
            for key, val in self.voice_map.items():
                print('    "' + key + '": "' + val.name + '"')
            print('  }')
            print('  Other-voices: ', list(map(lambda v: v.name, self.available_voices)))

        # self.available_voices = filter(lambda v: not v['reserved'], self.available_voices)

        return self

    def speak(self, text, **kwargs):
        if len(text) and config.get_value("use_tts", True):
            speaker = kwargs.get('speaker', 'Narrator')
            use_stream = config.get_value('tts_streaming')
            stability = config.get_float('tts_stability', .75)
            similarity = config.get_float('tts_similarity', .75)
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
        """remove and return a random voice from the remaining set"""
        if len(self.available_voices) == 0:
            if self.debug: print('all voices used, choosing random...')
            self.load_voice_map()
        # print('Remaining:', self.available_voice_names())
        return self.available_voices.pop(random.randrange(len(self.available_voices)))


if __name__ == '__main__':
    tts = TextToSpeech()
