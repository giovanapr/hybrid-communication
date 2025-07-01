# 📡 Hybrid-Communication

## 💡 Proposta de um Modelo Híbrido de Comunicação para Espaço Inteligente

Este repositório contém uma prévia da implementação de um modelo híbrido de comunicação voltado para espaços inteligentes. O modelo principal adotado é o **publish/subscribe**, e o modelo híbrido proposto combina essa abordagem com uma comunicação direta via **socket TCP**.

---

## ⚙️ Arquitetura Implementada

A proposta foi desenvolvida com base em três serviços principais:

### 🎥 Pub-Camera

O `pub-camera` é um serviço desenvolvido exclusivamente para testes e validação do modelo híbrido, sem a necessidade de alterações no gateway original da câmera.

**Funções principais:**
- Consome imagens do gateway da câmera.
- Publica imagens utilizando o padrão **publish/subscribe**.
- Implementa uma alternativa de comunicação via **socket TCP**.
- Expõe um **RPC** para receber comandos do orquestrador (para troca do modelo de comunicação).

---

### 🧍 Person-Detector

O `person-detector` é responsável pela detecção de pessoas nas imagens recebidas.

**Funções principais:**
- Inicialmente, consumia diretamente do gateway, mas foi adaptado para receber imagens do `pub-camera`.
- Utiliza um modelo **YOLO** para detecção de pessoas.
- Publica os resultados detectados.
- Foi adaptado para se comunicar via socket e alternar o modelo de comunicação conforme orientações recebidas.

> ℹ️ Para mais detalhes sobre o funcionamento original deste serviço, consulte o repositório **CITAR**.

---

### 🧠 Orquestrador

O `orquestrador` é o componente responsável por tornar a **camada de comunicação programável**, permitindo a adaptação dinâmica do modelo conforme o contexto.

**Funções principais:**
- Coleta métricas de desempenho a partir do **Zipkin** e do **Broker**.
- Toma decisões de mudança de modelo de comunicação com base nas métricas recebidas.
- Envia comandos para os serviços ajustarem seu modo de comunicação.

---

## 🚀 Considerações Finais

Esta implementação é uma prova de conceito voltada para a experimentação do modelo híbrido de comunicação em espaços inteligentes. Embora simplificada, ela demonstra a viabilidade da troca dinâmica de modelos de comunicação com base em métricas, visando melhorar o desempenho e a adaptabilidade do sistema.

