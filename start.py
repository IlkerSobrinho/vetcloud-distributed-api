import os
import subprocess
import sys
import time
import uvicorn
from api_clinica import app

# Sobe a API do Governo em background na porta 8001
subprocess.Popen([sys.executable, "-m", "uvicorn", "api_governo:app", "--host", "0.0.0.0", "--port", "8001"])
time.sleep(2)

# Sobe a API da Clínica na porta pública que a nuvem fornecer (ou 8000 local)
if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=porta)
