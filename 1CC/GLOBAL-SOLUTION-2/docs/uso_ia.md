# Uso de IA e validação crítica

O ChatGPT auxiliou amplamente a estruturação da atividade, a pesquisa de fontes, a redação e revisão das orientações, a implementação em Python, a preparação dos testes, a documentação e a montagem do vídeo de demonstração. A versão entregue deve ser lida, executada e compreendida pelo integrante antes do envio.

## Instruções comparadas

1. **Modelo A:** Responda com a orientação verificada e indique o órgão e o link.
2. **Modelo B:** Organize a orientação em blocos: assunto, próximo passo, fonte, data e abrangência. Termine indicando o limite do protótipo.

As duas instruções foram implementadas como templates em `src/sistema.py`. O conteúdo factual dos dois formatos vem do mesmo registro. Nenhum modelo externo é chamado pelo aplicativo. Um exemplo de uso no desenvolvimento foi pedir algumas perguntas fora de escopo ou ambíguas para que o sistema fosse avaliado também quando não deve escolher uma resposta.

## Validação feita

- As 15 fontes foram conferidas nas páginas de órgãos públicos em 17/11/2026. Cada orientação foi resumida e vinculada ao órgão e ao endereço consultado.
- Executamos o programa com 22 consultas e com seis tarefas de menu. A comparação usou as 15 orientações corretamente recuperadas, para isolar diferenças de apresentação.
- Os formatos receberam a mesma base. O formato B pontuou melhor na rubrica estrutural porque explicita próximos passos, abrangência e limite. Essa rubrica não mede percepção de clareza de usuários reais.
- Duas reformulações do conjunto de teste ficaram sem correspondência. As duas respostas e limitações seguem no CSV e no relatório.
- O vídeo mostra saídas produzidas pelo aplicativo local. Textos explicativos foram adicionados para leitura na tela.
