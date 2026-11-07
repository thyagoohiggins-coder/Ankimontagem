# Montador de Flashcards

Programa para **Windows** (Python + Qt) e app para **Android** (APK) para montar flashcards com **aprofundamento por trechos destacados**.
Pensado para estudo rápido em **tela dividida** ao lado do navegador: tudo fica numa coluna só, em forma de linha do tempo.

## Baixar
Na página de [Releases](../../releases), baixe:
- **MontadorDeFlashcards-Setup-x.y.z.exe**: instalador, com atalho no menu Iniciar e na área de trabalho.
- **MontadorDeFlashcards-portatil-x.y.z.exe**: versão portátil, abre sem instalar.

> O programa não tem assinatura digital. Se aparecer "O Windows protegeu o computador",
> clique em **Mais informações → Executar assim mesmo**.

## Android
Baixe **MontadorDeFlashcards-android-x.y.z.apk** na página de Releases e abra no celular
(o Android pede para permitir a instalação de apps de fora da Play Store).
- Tudo funciona por toque: selecione um trecho do BACK e toque em **🖍 Destacar** na barra que aparece embaixo;
  **🔗 Juntar** para estruturas separadas; toque num trecho vermelho e em **↪ Abrir sub-card** para ver o painel
  com o caminho (ex.: `initiatives → problems → thing`), **▲ Card pai** e os sub-cards.
- **☰ → Enviar para o Anki**: gera o `.apkg` no celular e abre no **AnkiDroid** (ou compartilha/salva o arquivo).
- **☰ → Exportar/Importar backup**: o mesmo arquivo `.json` do programa do Windows, para levar os cards de um
  para o outro.
- O botão Voltar do Android fecha painéis, a barra e o estudo.

> **Atualizar sem perder nada:** antes de instalar uma versão nova, faça ☰ → Exportar backup. Se o Android
> disser que o app não pode ser instalado por cima, desinstale o antigo, instale o novo e importe o backup.
> Para as versões novas instalarem sempre por cima, cadastre uma chave de assinatura fixa nos segredos do
> repositório (`ANDROID_KEYSTORE_B64` e `ANDROID_KEYSTORE_PASSWORD`).

A interface do Android fica em `android/app/src/main/assets/www` e o app nativo em `android/`.

## Como usar
1. **+ Novo** cria um card raiz. Escreva o **FRONT**, aperte **Tab** e escreva o **BACK**
   (o texto do back sai em **azul Tiffany**).
2. No BACK, selecione um trecho que você não conhece e aperte **Ctrl+D** (ou clique em **🖍 Destacar**
   na barra que aparece ao selecionar, ou use o botão direito). O trecho fica **vermelho** e um novo card
   aparece na linha do tempo. Destaque quantos trechos quiser.
3. Clique num card da linha do tempo (ou **Alt+↓**) para abri-lo e destacar trechos no BACK dele.
   Não há limite de profundidade, e cada trecho segue seu próprio ramo.
4. Cada card mostra quantos trechos foram destacados nele. No topo aparece o total a partir da raiz;
   clique em **resumo ›** (ou **Ctrl+R**) para ver o detalhamento.
5. **▶ Estudar** (F5) mostra os cards do **último sub-card adicionado até o card raiz**.
   Espaço vira, ← → navegam, + / − mudam o tamanho do texto, Esc volta.

### Estruturas separadas (ex.: phrasal verb “got … back”)
- Em *I **got** my earphones **back***: selecione “got” e clique em **🔗 Juntar** (aparece na barra ao selecionar,
  ou Ctrl+J / botão direito). Depois selecione “back” e destaque (**Ctrl+D**). As partes viram **um único
  sub-card** com front “got back”. Dá para juntar mais de duas partes; **Esc** cancela.

### Janelinhas de sub-cards
- **Ctrl+clique** num trecho vermelho, ou botão direito → *Abrir sub-card deste trecho*, abre o sub-card numa
  janelinha. Clique num trecho vermelho dela (ou nos links **↓ Sub-cards** no rodapé) para **descer**;
  **▲ Card pai** (ou ↑) **sobe** até a raiz. Para começar de um sub-card e voltar: ⋯ do card → *Ver em pop-ups*.
- O topo mostra o **caminho** do card a partir da raiz, ex.: `initiatives → problems → thing`
  (a palavra sublinhada do front, ou o trecho destacado).
- As janelinhas podem ser **movidas** (arraste o topo), **redimensionadas** (qualquer borda ou o canto) e
  **minimizadas** (— ou duplo clique no topo). O último tamanho fica lembrado e vale para todas.
- **Enter** ou **✎ Editar** abre o card para editar; **Esc** ou ✕ fecha a janelinha e as abertas a partir dela.

### Visualização
☰ → **Visualização dos cards**:
- **Linha do tempo (vertical)**: uma coluna só, boa para tela dividida.
- **Grade em 2 colunas**: 1º card no alto à esquerda, 2º à direita, 3º abaixo do 1º, 4º abaixo do 2º, e assim
  por diante. As janelinhas de sub-cards também se organizam nessa grade.

### Enviar para o Anki
- ☰ → **Enviar para o Anki…** (Ctrl+E) envia o card raiz e todos os sub-cards com as mesmas cores e formatação.
- **Baralho:** escolha um baralho que já existe no Anki (a lista vem do AnkiConnect; ↻ atualiza) ou digite um
  nome novo. O último usado fica lembrado. No `.apkg`, usar o nome de um baralho existente faz os cards entrarem nele.
- Escolha a ordem: **sub-cards primeiro, do último até o card raiz** (padrão) ou o card raiz primeiro.
- **Direto no Anki:** com o Anki aberto e o complemento **AnkiConnect** (código `2055492159`). É criado o tipo de
  nota "Montador de Flashcards" (campos Frente e Verso) e o back fica em azul Tiffany.
  Reenviar atualiza os cards já enviados, sem duplicar.
- **Tamanho do texto:** o texto normal fica do tamanho escolhido em *Tamanho do texto normal no Anki* (com o Anki
  aberto, o programa usa o mesmo tamanho dos outros cards do baralho). O que você aumentou ou diminuiu no programa
  fica proporcional.
- **Sem AnkiConnect:** *Salvar arquivo…* gera um **Pacote de Baralho do Anki (.apkg)**: dê dois cliques nele
  (ou Arquivo → Importar) e o baralho entra com o tipo de nota, as cores, a formatação e a ordem. Importar de novo
  atualiza os mesmos cards. Também dá para salvar como **Notas em Texto Puro (.txt)** (tipo Básico).

### Texto
- A barra de formatação só aparece quando há texto selecionado: negrito, itálico, sublinhado, tachado,
  **cor da fonte**, **cor do sublinhado**, tamanho e limpar formatação.
- **A formatação é lembrada:** o último tamanho de fonte e a última formatação escolhidos (negrito, itálico,
  sublinhado, tachado, cor da fonte e cor do sublinhado) viram o padrão do texto novo, inclusive depois de
  fechar o programa. FRONT e BACK guardam cada um a sua. Num card ou parágrafo vazio vale o padrão; dentro de
  um texto já escrito, o novo texto segue o texto ao redor. **⌫ / Ctrl+Espaço** ou ☰ → *Restaurar formatação
  padrão* voltam ao original (tamanho 11.5, back em azul Tiffany).
- O tamanho do texto no modo de estudo (+ / −) também é lembrado.
- **Colar sem formatação**: ligado por padrão no Ctrl+V (menu ☰). Ctrl+Shift+V sempre cola sem formatação;
  o botão direito também oferece "Colar com formatação".
- O botão direito abre um menu completo em português.
- O trecho destacado fica com texto e sublinhado vermelhos. A **sombra vermelha** atrás dele é opcional:
  ☰ → *Sombra vermelha nos trechos destacados* (fica salvo).

### Tela dividida
- A janela funciona a partir de 360 px de largura.
- Menu ☰ → **Fixar janela sempre no topo**, para estudar com o Chrome aberto.

Os cards ficam salvos automaticamente em `%APPDATA%\MontadorFlashcards\Montador de Flashcards\flashcards.json`.
Use ☰ → Exportar/Importar para backup.

## Rodar a partir do código
```bash
pip install -r requirements.txt
```
```bash
python main.py
```
Testes: `python -m unittest discover -s tests`. Os `.exe` são gerados pelo GitHub Actions
(`.github/workflows/build-windows.yml`). Para publicar uma release, rode o workflow manualmente
informando a tag (ex.: `v2.1.0`) depois de mudar a versão em `montador/__init__.py`.
