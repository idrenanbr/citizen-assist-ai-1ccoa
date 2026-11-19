# Uso de IA e validação crítica

O ChatGPT foi usado na pesquisa de fontes e na redação das orientações, na geração e revisão do código Python, na preparação dos testes e na elaboração da documentação e do vídeo.

## Instruções comparadas

1. **Modelo A:** Responda com a orientação verificada e indique o órgão e o link.
2. **Modelo B:** Organize a orientação em blocos: assunto, próximo passo, fonte, data e abrangência. Termine indicando o limite do protótipo.

As duas instruções foram implementadas como templates em `src/sistema.py`. O conteúdo factual dos dois formatos vem do mesmo registro. Nenhum modelo externo é chamado pelo aplicativo. Um exemplo de uso no desenvolvimento foi pedir algumas perguntas fora de escopo ou ambíguas para que o sistema fosse avaliado também quando não deve escolher uma resposta.

## Validação feita

- As 15 fontes foram conferidas nas páginas de órgãos públicos em 17/11/2026. Cada orientação foi resumida e vinculada ao órgão e ao endereço consultado.
- Os testes automatizados cobriram 22 consultas e seis tarefas de menu. A comparação usou as 15 orientações corretamente recuperadas, para isolar diferenças de apresentação.
- Os formatos receberam a mesma base. O formato B pontuou melhor na rubrica estrutural porque explicita próximos passos, abrangência e limite. Essa rubrica não mede percepção de clareza de usuários reais.
- Duas reformulações do conjunto de teste ficaram sem correspondência. As duas respostas e limitações seguem no CSV e no relatório.
- O vídeo mostra saídas produzidas pelo aplicativo local. Textos explicativos foram adicionados para leitura na tela.
