import datetime

class StorageService:

    def save_transcript(self, text):

        filename = f"transcripts_{datetime.datetime.now().timestamp()}.txt"

        with open(filename, "w") as f:
            f.write(text)

        print("Transcript saved:", filename)
