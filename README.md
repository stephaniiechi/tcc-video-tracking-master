# tcc-video-tracking

allowed python versions 2.7, 3.5, 3.6, 3.7, 3.8

pip install -r requirements.txt

python video_device_listing/setup.py install

Para gerar o executável:
pyinstaller --onefile -w -n ar-tracking -i icon.ico main.py


Alguns erros que podem aparecer se você for mexer com os códigos

* -------------- ERRO COM A BIBLIOTECA PIL/PILLOW -------------- *
from PIL import ImageTk, Image
ModuleNotFoundError: No module named 'PIL'

- Certifique-se de que não está instalada a biblioteca PIL ao invés da Pillow. 
	- Para a Pillow funcionar, você deve desinstalar a PIL (que foi substituída pela Pillow)

- Se mesmo assim não rodar, verificar o local onde a biblioteca foi instalada:
	- Ex.: C:\Users\user\AppData\Local\Programs\Python\Python310\Lib\site-packages
	- Aqui você verá uma pasta chamada 'pil'/'PIL'
	- Se estiver como 'pil', mude o import para 'from pil import ...' (letra maiúscula/minúscula importa!)


* -------------- ERRO COM A BIBLIOTECA PYREBASE/CRYPTO/PYCRYPTODOME -------------- *
from Crypto.PublicKey import RSA
ModuleNotFoundError: No module named 'Crypto.PublicKey'

- Assim como o PIL, o Crypto foi substituído pelo Pycryptodome

- Certifique-se de ter instalado o 'pycryptodome' -> (pip install pycryptodome)
- Se mesmo assim não rodar, verificar o local onde a biblioteca foi instalada:
	- Ex.: C:\Users\user\AppData\Local\Programs\Python\Python310\Lib\site-packages
	- Abra a pasta '\Crypto'
	- Renomeie as pastas que estão dando erro, exemplo a seguir:
		- ModuleNotFoundError: No module named 'Crypto.PublicKey'
			- Renomear a pasta 'publickey' para 'PublicKey'
		- ModuleNotFoundError: No module named 'Crypto.Util'
			- Renomear a pasta 'util' para 'Util'
		- Fazer o mesmo para todos os erros que tiver
- Se nada disso funcionar, tente instalar as bibliotecas em um ambiente virtual (ao invés do global)
