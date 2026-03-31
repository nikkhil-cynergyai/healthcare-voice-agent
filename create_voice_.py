import base64
from mistralai import Mistral

client = Mistral(api_key='djtcChjF5Y5pMlfIRwurQBygR0aUZ5jD')

audio_b64 = base64.b64encode(open('mp3-output-ttsfree_dot_com.mp3', 'rb').read()).decode()

voice = client.audio.voices.create(
    name='sarah-billing',
    sample_audio=audio_b64,
    sample_filename='sample.mp3',
    languages=['en'],
    gender='female'
)
print('Voice ID:', voice.id)