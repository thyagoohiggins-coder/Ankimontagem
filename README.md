# Montador de Flashcards

Programa nativo para Windows (Python + Qt) para montar flashcards com **aprofundamento por trechos destacados**.
Pensado para estudo rápido em **tela dividida** ao lado do navegador: tudo fica numa coluna só, em forma de linha do tempo.

## Baixar
Na página de [Releases](../../releases), baixe:
- **MontadorDeFlashcards-Setup-x.y.z.exe**: instalador, com atalho no menu Iniciar e na área de trabalho.
- **MontadorDeFlashcards-portatil-x.y.z.exe**: versão portátil, abre sem instalar.

> O programa não tem assinatura digital. Se aparecer "O Windows protegeu o computador",
> clique em **Mais informações → Executar assim mesmo**.

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

### Pop-ups de sub-cards
- **Ctrl+clique** num trecho vermelho, ou botão direito → *Abrir sub-card deste trecho*, abre o sub-card num pop-up
  logo abaixo, como um menu.
- No pop-up, clicar num trecho vermelho abre o próximo pop-up **descendo**; **▲ Card pai** (ou ↑) abre o card
  anterior **subindo** até a raiz. Para começar de um sub-card e voltar: ⋯ do card → *Ver em pop-ups*.
- **Enter** ou **✎ Editar** abre o card na linha do tempo; **Esc** ou clicar fora fecha.

### Enviar para o Anki
- ☰ → **Enviar para o Anki…** (Ctrl+E) envia o card raiz e todos os sub-cards com as mesmas cores e formatação.
- Escolha a ordem: **sub-cards primeiro, do último até o card raiz** (padrão) ou o card raiz primeiro.
- **Direto no Anki:** com o Anki aberto e o complemento **AnkiConnect** (código `2055492159`). É criado o tipo de
  nota "Montador de Flashcards" (campos Frente, Verso, Origem, Nível) e o back fica em azul Tiffany.
  Reenviar atualiza os cards já enviados, sem duplicar.
- **Sem AnkiConnect:** *Salvar arquivo…* gera um `.txt` para importar em Arquivo → Importar (tipo Básico).

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
