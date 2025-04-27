import requests
import os

os.system('cls')

response = requests.post(
    'http://localhost:11434/api/generate',
    json={
        'model': 'gemma3',
        'prompt': u'''sku:Small Pop 40gx12pcsx4trays.
          Извлеки в формате json.
            {
                "sku": str,  # Bubble Bubble Water(Fruits) 55mlx24pcsx12boxes
                "grm": float,  # 55
                "pcs_in_block": float,  # 24
                "box_in_cartoon": int,  # 12
                "pcs_type": str,  # ml
                "box_type": str  # box
            }
        ''',
        'stream': False
    }
)

print(response.json()['response'])
