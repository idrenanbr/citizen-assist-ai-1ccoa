# Citizen Assist AI

Global Solution 2026.2 · FIAP ON · Ciência da Computação · 1CCOA

**Equipe:** Citizen Assist AI  
**Integrante:** Renan Mano Otero · RM 554911 · entrega individual

## Problema e público

Informações sobre documentos, serviços digitais e apoio comunitário estão espalhadas por páginas de órgãos diferentes. Este protótipo ajuda quem precisa localizar um primeiro passo e chegar à fonte oficial. A base cobre serviços nacionais e alguns serviços do estado ou do município de São Paulo, identificados na resposta.

## Executar

Requer Python 3.10 ou superior. Usa somente a biblioteca padrão. A partir da pasta que contém este README:

```bash
python src/sistema.py
python src/sistema.py --pergunta "Como encontro a UBS de referência?"
python src/sistema.py --modelo A --pergunta "Como encontro a UBS de referência?"
python tests/avaliar.py
```

O menu aceita perguntas em português e os números 1, 2 e 3. Cada tema mostra subtemas, atalhos por ID e temas relacionados. Digite `/temas` para voltar à busca geral ou `/sair` para encerrar. Os números de tema também funcionam durante a navegação. A opção `--base` permite testar outro JSON.

### Exemplos

| Entrada | Comportamento |
|---|---|
| `Qual é a UBS do meu bairro?` | Orienta a usar o Busca Saúde da Prefeitura de São Paulo e exibe a referência. |
| `CPF e passaporte` | Mostra os dois assuntos empatados e pede que o usuário escolha um deles. |
| `Como consertar uma torneira?` | Informa ausência de conteúdo verificado e oferece os temas disponíveis. |
| Entrada vazia ou opção `99` | Explica como prosseguir. |
| `1` e depois `doc-cpf` | Abre Documentos e seleciona a orientação cadastrada por ID. |

O exemplo abaixo mostra a saída do modelo B para a pergunta “Qual é a UBS do meu bairro?”.

> **Assunto:** Localização de UBS em São Paulo  
> **Próximo passo:** Use o Busca Saúde da Prefeitura de São Paulo para localizar estabelecimentos da rede SUS do município. Para a UBS de referência, pesquise o endereço na ferramenta oficial e confirme os dados da unidade.  
> **Fonte:** [Prefeitura de São Paulo • Secretaria Municipal da Saúde](https://prefeitura.sp.gov.br/web/saude/w/busca-saude)  
> **Verificação:** 2026-11-17 · **Abrangência:** Município de São Paulo  
> **Limite:** Protótipo informativo. Confirme documentos, horários e condições no canal oficial.

## Base e busca

[`data/base.json`](data/base.json) contém 15 registros verificados em 17/11/2026, cinco para cada tema: Documentos, Serviços digitais e Apoio comunitário. Cada registro traz ID, tema, subtema, pergunta de referência, palavras-chave, orientação, órgão, URL HTTPS, abrangência e data de verificação. As fontes estão no próprio JSON e no apêndice do relatório.

O sistema valida o JSON ao iniciar. Ele usa listas para organizar assuntos e dicionários para indexar IDs e agrupar orientações por tema. O menu apresenta a hierarquia tema → subtema → orientação. O campo `relacionados` representa um grafo simples entre os três temas. As relações levam de documentos aos serviços em que são usados e de serviços digitais aos canais de apoio.

A busca normaliza acentos, pontuação e caixa. Um ID ou uma formulação que coincide com o alias completo recebe 100 pontos. Em correspondências parciais, a pontuação é `4 × número de palavras do alias + 1`. A comparação respeita fronteiras de palavra. Cada registro mantém sua maior pontuação, sem somar sinônimos repetidos. O melhor candidato é mostrado. Um empate pede esclarecimento e uma busca sem candidatos retorna um limite explícito. O modo por tema filtra os registros antes da comparação. Para atualizar a base, acrescente ou edite registros no JSON e repita a avaliação.

## Modelos de resposta

- **A — direto:** apresenta a orientação e a fonte em dois blocos.
- **B — guiado:** apresenta assunto, próximo passo, órgão, link, data, abrangência e limite. É o padrão porque deixa claros o recorte geográfico e a necessidade de confirmação no canal oficial.

Os dois modelos são instruções documentadas e aplicadas por templates determinísticos. O aplicativo funciona localmente, sem enviar perguntas a um serviço externo. Em caso de informação insuficiente, ele dispensa uma resposta factual e sugere como reformular ou escolher um tema.

## Testes e resultados

A rodada de referência obteve **20 acertos em 22 cenários (90,9%)**, **6 de 6 tarefas do roteiro de usabilidade** e **5 de 5 condições de erro da base** tratadas. O tempo registrado é o de busca e formatação em memória, sem inicialização, rede ou digitação. Veja [métricas](docs/metricas.json), [perguntas e respostas](docs/resultados_testes.csv), [comparação dos modelos](docs/comparacao_modelos.csv), [roteiro de usabilidade](docs/roteiro_usabilidade.csv) e [validação da base](docs/validacao_base.csv).

Os erros observados foram duas reformulações sem aliases reconhecidos. O roteiro foi automatizado no terminal e mede conclusão de tarefas observáveis. Uma avaliação com moradores testaria compreensão, satisfação e acessibilidade em outros contextos.

## Privacidade, acessibilidade e manutenção

O protótipo não pede identificação, não grava consultas e sinaliza padrões comuns de CPF, telefone e e-mail. Digite o assunto sem dados pessoais. O terminal usa rótulos de texto, saída sem dependência de cores e navegação por teclado. O link da fonte aparece por extenso. Confirme abrangência, horários, condições e documentos diretamente com o serviço responsável.

A comparação ainda depende do vocabulário da base. Como próximos passos, testar reformulações com pessoas que não viram os aliases, adicionar apenas sinônimos validados, programar revisão periódica das fontes e testar o fluxo com leitor de tela.

- [Relatório técnico](docs/relatorio.pdf)
- [Uso de IA e validação](docs/uso_ia.md)
