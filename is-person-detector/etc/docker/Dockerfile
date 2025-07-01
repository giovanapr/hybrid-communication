# Fase de Build
FROM nvcr.io/nvidia/cuda:11.6.1-cudnn8-devel-ubuntu20.04 AS build

ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Instalando dependências essenciais
RUN apt-get -y update && apt-get install -y --no-install-recommends  \
        build-essential gcc g++ git wget cmake unzip pkg-config  \
        python3 python3-dev python3-setuptools python3-pip python3-venv \
        libatlas-base-dev libopenblas-dev liblapack-dev gfortran && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# Criando ambiente virtual e instalando pacotes essenciais
RUN python3 -m venv $VIRTUAL_ENV && \
    $VIRTUAL_ENV/bin/pip install --upgrade pip wheel numpy

# Copiando e instalando dependências do projeto
WORKDIR /opt/is_person_detector
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copiando o restante do código
COPY . .

# Fase de Runtime (imagem final)
FROM nvcr.io/nvidia/cuda:11.6.1-cudnn8-runtime-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copia o ambiente virtual e o código do modelo
COPY --from=build /opt/.venv /opt/.venv
COPY --from=build /opt/is_person_detector /opt/is_person_detector

# Instalando apenas as dependências necessárias para execução
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 libpng16-16 libjpeg-turbo8 libtiff5 libwebp6 libgl1-mesa-glx libglib2.0-0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Definindo o diretório de trabalho
WORKDIR /opt/is_person_detector/is_person_detector
CMD ["python3", "stream.py"]
