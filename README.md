# Montador de Flashcards

Aplicativo web (HTML + CSS + JavaScript puro, sem instalação) para montar flashcards com **aprofundamento por trechos destacados**.

## Como usar

Abra o `index.html` no navegador. Os dados ficam salvos automaticamente no navegador (localStorage). Use **Exportar/Importar** para fazer backup em JSON.

1. Clique em **+ Novo card raiz** e preencha o **FRONT** e o **BACK**.
   - Os dois lados têm formatação: negrito, itálico, sublinhado, tachado, tamanho, **cor da fonte**, **cor do sublinhado** e listas.
   - O texto do BACK vem em **azul Tiffany** (`#0ABAB5`) por padrão.
2. No BACK, selecione um trecho que você não conhece e clique em **🖍 Destacar seleção**
   (ou ligue o **Modo destaque** e apenas selecione o texto com o mouse).
   - O trecho fica **vermelho** e um novo par FRONT/BACK (sub-card) aparece logo abaixo.
   - Você pode destacar quantos trechos quiser em cada BACK.
3. Clique em **Aprofundar →** num sub-card para destacar trechos no BACK dele, e assim por diante, sem limite de profundidade.
   Cada trecho da raiz pode ter sua própria ramificação independente.
4. Cada card mostra quantos trechos foram destacados nele; a árvore lateral mostra a contagem de todos.
5. Clique em **✔ Concluir aprofundamento** para ver quantos trechos foram destacados a partir do card raiz,
   o detalhamento por card e a ordem de estudo.
6. **▶ Estudar**: os cards são mostrados do **último sub-card adicionado para o primeiro**, terminando no card raiz.
   Atalhos: `Espaço` vira, `←`/`→` navegam, `Esc` sai.

Outros detalhes:
- Clicar num trecho vermelho leva ao sub-card correspondente.
- **🗑 Remover destaque** remove o trecho destacado e o sub-card (com seus descendentes). Apagar o trecho vermelho do texto tem o mesmo efeito.
