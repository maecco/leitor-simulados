# leitor-simulados

### Sumário

1. [Introdução](#introdução)
2. [Requerimentos](#requerimentos)
3. [Setup do programa](#setup-do-programa)  
4. [Uso - Web Application](#uso---web-application)
5. [Uso - CLI (Legacy)](#uso---cli-legacy)
6. [API Endpoints](#api-endpoints)
7. [For Devs](#for-devs)


## Introdução
Algoritmo para fazer a leitura de cartões de respostas de simulados utilizando Visão Computacional.

**Versão 2.0** - Agora disponível como aplicação web com interface moderna!

## Requerimentos
Antes de começar a instalação, é necessário que os seguintes itens estejam instalados na sua máquina:  
1. `python>=3.10`  
O download para Mac, Windows e Linux pode ser feito no site oficial do Python:
> https://www.python.org/downloads/
2. `Docker` (opcional, para deploy containerizado)
O guia para a instalação pode ser encontrado em:
> https://docs.docker.com/engine/install/

## Setup do programa

### Opção 1: Instalação Local (Recomendado para desenvolvimento)
```bash
# Clone o repositório
git clone <repo-url>
cd leitor-simulados

# Crie um ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt
```

### Opção 2: Docker
```bash
docker compose up -d --build
```

## Uso - Web Application

### Executando o servidor web

```bash
# Método simples
python run_web.py

# Com opções
python run_web.py --port 8080 --reload  # Desenvolvimento com auto-reload
python run_web.py --workers 4           # Produção com múltiplos workers
```

Acesse `http://localhost:8000` no navegador.

### Docker
```bash
docker compose up -d
# Acesse http://localhost:8000
```

### Funcionalidades da Interface Web
1. **Criar Sessão**: Selecione o tipo de prova (PS_ALUNOS, SIMULINHO, SIMUFSC, SIMUENEM)
2. **Upload de Imagens**: Arraste e solte ou selecione múltiplas imagens
3. **Configurar Modelos**: Escolha os modelos de detecção e ajuste os thresholds
4. **Processar**: Processe uma ou todas as imagens
5. **Visualizar Resultados**: Veja as detecções na imagem e as respostas identificadas
6. **Editar Respostas**: Corrija manualmente respostas se necessário
7. **Exportar**: Baixe os resultados em JSON ou CSV

## Uso - Desktop Client

O cliente desktop é uma aplicação leve que se conecta ao servidor para processamento.

### Requisitos do Cliente
```bash
pip install requests pillow
```

### Executando o Cliente
```bash
# Conectar ao servidor local
python run_client.py

# Conectar a servidor remoto
python run_client.py --server http://servidor:8000
```

### Funcionalidades do Cliente Desktop
- **Conexão ao servidor**: Conecte a qualquer servidor Leitor de Simulados
- **Upload de imagens**: Carregue imagens locais para processamento no servidor
- **Visualização**: Veja as imagens com detecções sobrepostas
- **Navegação**: Use setas ◀ ▶ ou teclado para navegar entre imagens
- **Edição de respostas**: Corrija respostas manualmente
- **Exportação**: Salve resultados em JSON ou CSV

### Arquitetura Cliente-Servidor
```
┌─────────────────┐         HTTP/REST         ┌─────────────────┐
│  Desktop Client │ ◄─────────────────────────► │   Web Server    │
│   (Leve, GUI)   │                            │ (Processamento) │
│                 │                            │                 │
│  - Upload imgs  │                            │  - ML Models    │
│  - View results │                            │  - Detection    │
│  - Edit answers │                            │  - Reports      │
└─────────────────┘                            └─────────────────┘
```

## API Endpoints

A aplicação expõe uma API REST completa:

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/session/create` | Criar nova sessão |
| GET | `/api/session/{id}` | Obter info da sessão |
| DELETE | `/api/session/{id}` | Deletar sessão |
| GET | `/api/models` | Listar modelos disponíveis |
| POST | `/api/upload/{session_id}` | Upload de imagens |
| GET | `/api/images/{session_id}` | Listar imagens da sessão |
| GET | `/api/image/{session_id}/{image_id}` | Obter imagem |
| POST | `/api/process/{session_id}/{image_id}` | Processar imagem |
| POST | `/api/process-all/{session_id}` | Processar todas |
| GET | `/api/report/{session_id}/{image_id}` | Obter relatório |
| GET | `/api/reports/{session_id}` | Obter todos relatórios |
| POST | `/api/update-answer/{session_id}/{image_id}` | Atualizar resposta |
| GET | `/api/export/{session_id}` | Exportar resultados |

## Uso - CLI (Legacy)

A interface gráfica desktop ainda está disponível em `src/`:

```bash
python src/leitor_de_simulados.py
```

### Script de linha de comando (antigo):
```bash
docker exec -it detection_dev_environment /bin/bash
python3 ./src/exam_scanner.py --prova <TIPO_DE_PROVA> --input_directory <INPUT_DIR_PATH>
```

## For Devs
### EFscanAlgo
#### Adicionando pipeline
É possivel implementar novas pipelines de correção das provas dentro do algoritimo de correção convencional, para fazer isso é preciso:  

Criar um arquivo `.py` dentro de `models/EFscanAlgo/first_stage` ou `models/EFscanAlgo/first_stage` dependendo do estagio que se deseja implementar.  

![Screenshot from 2024-08-17 20-35-25](https://github.com/user-attachments/assets/ea6b6770-502c-461e-aa24-7099d381079f)  

O arquivo de pipeline deve conter implementada uma funçao chamada `detect` que será chamada pelo algoritimo principal, para cada imagem a ser analisada, e cuja assinatura deve ser a seguinte:  

![Screenshot from 2024-08-17 20-15-47](https://github.com/user-attachments/assets/a97d4378-cdaa-465f-b409-e6003689c17a)  

Onde:  
- `scanner` é a classe base do algoritimo
- `img` é da classe `core.image.Image` contendo a imagem a ser processada.
- `Detection` é a classe cuja `core.object_detecion.Detection`

#### Init Pipeline
O arquivo de pipeline tambem pode conter uma função chamada `init_pipeline`, que pode ser implementada ou nao, e que será chamada uma vez apenas. A funçao deve ter a seguinte assinatura:

![Screenshot from 2024-08-17 21-03-08](https://github.com/user-attachments/assets/aef297ea-9fc9-4090-a3aa-d54575cd0977)  

Onde:  
- `scanner` é a classe base do algoritimo
- `config` é um dicionario que contem informaçoes:
![Screenshot from 2024-08-17 21-23-06](https://github.com/user-attachments/assets/8f74704f-d95b-452a-a86b-d0290996ba75)  
**Repare que, em `stage` é a real faze em que esta sendo corrigida, e em `model->stage` é o estagio que o modelo supostamente deve corrigir. (É possivel selecionar um modelo de correçao do segundo estagio para corrigir o primeiro estagio, embora isso nao faça muito sentido.)


#### Exemplo de uso:
Essa funçao pode ser usada para iniciar variáveis que serão usadas na funçao `detect` como na pipeline `ef_default_algo` onde é iniciado um modelo yolo que sera futuramente usado para encontrar os cpfs:  
Em `init_pipeline`:  
![Screenshot from 2024-08-17 21-11-10](https://github.com/user-attachments/assets/e46e162d-fe31-41ef-87a0-c2189eb27cd5)  

Em `detect`:  
![Screenshot from 2024-08-17 21-12-54](https://github.com/user-attachments/assets/5414abba-4e9e-4385-a6cd-fae6efa254b6)  


