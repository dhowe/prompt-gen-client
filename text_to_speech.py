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
        reserved_voices = []
        for i, row in enumerate(rows):
            if i < 2: continue
            char_name = row[0].strip()
            if len(char_name) == 0: continue
            voice_name = row[1].strip()
            if len(voice_name) == 0: continue
            reserved = row[2].strip() == 'TRUE'
            # print(char_name, voice_name, reserved)
            voice = find(lambda v: v.name == voice_name, self.voices)
            if not voice:
                print(f'bad voice mapping, ignoring "{char_name}" -> "{voice_name}"')
                continue
            if reserved:
                if voice in self.available_voices:
                    self.available_voices.remove(voice)
                reserved_voices.append(voice)
            if not char_name.startswith('__'):
                self.voice_map[char_name] = voice

        # ### TESTING - REMOVE
        # del self.voice_map['Beetle 1']
        # del self.voice_map['Beetle 2']
        # del self.voice_map['Beetle 3']
        # self.available_voices = [self.voice_by_name('Domi'), self.voice_by_name('Bella')]

        if self.debug:
            print('  Voice-mappings: {')
            for key, val in self.voice_map.items():
                print('    "' + key + '": "' + val.name + '"')
            print('  }')
            print('  Reserved-voices:  ', list(map(lambda v: v.name, reserved_voices)))
            print('  Available-voices: ', list(map(lambda v: v.name, self.available_voices)))

        return self

    def voice_by_name(self, name):
        return find(lambda v: v.name == name, self.voices)

    def speak(self, text, **kwargs):
        if len(text) and config.get_value("use_tts", True):
            random_voice = False
            speaker = kwargs.get('speaker', 'Narrator')
            use_stream = config.get_value('tts_streaming')
            stability = config.get_float('tts_stability', .75)
            similarity = config.get_float('tts_similarity', .75)
            voice = None
            if speaker and len(speaker):
                voice = self.voice_map.get(speaker, None)
                if not voice:
                    random_voice = True
                    voice = self.get_available_voice()
                    self.voice_map[speaker] = voice

            if not voice:
                random_voice = True
                voice = self.last_voice

            if not voice:
                print(f'[TTS] Fatal error: no voice for {speaker}, last={self.last_voice}')
                return

            if voice.settings:
                voice.settings.stability = stability
                voice.settings.similarity_boost = similarity

            audio = generate(text=text, voice=voice, stream=use_stream)

            if self.debug: print(f'/tts \'{speaker}\'/\'{voice.name}\' -> {text} ' +
                                 f'[sta={stability}, sim={similarity}{" rand" if random_voice else ""}]')
            if use_stream:
                stream(audio)
            else:
                play(audio)

            self.last_voice = voice  # save the active voice as last_voice

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
