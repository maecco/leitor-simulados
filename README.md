# Leitor de Simulados API

API REST para processamento de folhas de resposta de simulados usando modelos de detecção YOLO.

## Estrutura do Projeto

```
├── src/              # Código da API FastAPI
│   ├── main.py          # Endpoints da API
│   ├── schemas.py       # Schemas Pydantic
│   ├── core/            # Lógica de detecção e processamento
│   └── services/        # Serviços de negócio
├── models/              # Modelos de detecção
│   ├── YoloV8/         # Modelos YOLO
│   └── LabelMaps.json  # Mapeamento de labels
├── tests/              # Testes automatizados
├── run.py              # Script de execução
├── requirements.txt    # Dependências Python
├── Dockerfile          # Imagem Docker
└── docker-compose.yml  # Composição Docker
```

## Instalação

### Requisitos
- Python 3.10+
- pip

### Configuração

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

## Execução

### Desenvolvimento
```bash
python run.py --reload
```

### Produção
```bash
python run.py --workers 4
```

### Docker
```bash
docker-compose up -d
```

## API Endpoints

A documentação interativa está disponível em `/docs` após iniciar o servidor.

### Principais Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/health` | Health check |
| GET | `/api/models` | Lista modelos disponíveis |
| POST | `/api/session/create` | Cria sessão de trabalho |
| POST | `/api/upload/{session_id}` | Upload de imagens |
| GET | `/api/images/{session_id}` | Lista imagens da sessão |
| POST | `/api/process/{session_id}/{image_id}` | Processa imagem |
| GET | `/api/report/{session_id}` | Obtém relatório |
| POST | `/api/export/{session_id}/csv` | Exporta para CSV |

### Exemplo de Uso

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Criar sessão
session = requests.post(f"{BASE_URL}/session/create").json()
session_id = session["session_id"]

# Upload de imagem
with open("imagem.jpg", "rb") as f:
    files = {"file": f}
    response = requests.post(f"{BASE_URL}/upload/{session_id}", files=files)
    image_id = response.json()["images"][0]["id"]

# Processar imagem
process_data = {
    "first_stage_model": "YoloV8/first_stage/general_fs.pt",
    "second_stage_model": "YoloV8/second_stage/general_ss_v2.pt",
    "test_type": "PS_ALUNOS"
}
result = requests.post(
    f"{BASE_URL}/process/{session_id}/{image_id}",
    params=process_data
).json()

print(result["report"])
```

## Testes

```bash
# Rodar todos os testes
pytest

# Testes com output detalhado
pytest -v -s

# Testes de integração (requerem modelos)
pytest tests/test_integration_processing.py -v -s
```

## Modelos

### First Stage (Primeiro Estágio)
Detecta blocos na folha de resposta:
- `CPF_BLOCK` - Bloco de CPF
- `QUESTION_BLOCK` - Bloco de questões

### Second Stage (Segundo Estágio)
Detecta elementos dentro dos blocos:
- `SELECTED_BALL` - Bolinha marcada
- `UNSELECTED_BALL` - Bolinha não marcada

## Licença

MIT License - veja [LICENSE](LICENSE)


