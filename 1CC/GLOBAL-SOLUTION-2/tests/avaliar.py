"""Executa cenários reproduzíveis e grava evidências da avaliação."""
import csv
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from sistema import Assistente, BASE_PADRAO, ErroBase, LIMITE, MODELOS  # noqa: E402

CASOS = [
    ("01", "direta", "Como tirar a primeira via da CIN em São Paulo?", "doc-cin"),
    ("02", "reformulação", "Quero saber a regularidade do CPF.", "doc-cpf"),
    ("03", "reformulação", "Quero a minha habilitação digital.", "doc-cnh"),
    ("04", "direta", "Onde tiro a certidão de quitação eleitoral?", "doc-eleitoral"),
    ("05", "direta", "Por onde começo a solicitar um passaporte?", "doc-passaporte"),
    ("06", "direta", "Como criar minha conta GOV.BR?", "dig-criar"),
    ("07", "reformulação", "Não lembro a senha do GOV.BR.", "dig-senha"),
    ("08", "direta", "Onde vejo meus requerimentos do INSS?", "dig-inss"),
    ("09", "reformulação", "Onde estão os meus vínculos de emprego?", "dig-ctps"),
    ("10", "direta", "Como consultar relatórios do Banco Central sobre minhas contas?", "dig-registrato"),
    ("11", "direta", "Onde encontro um CRAS em São Paulo?", "apo-cras"),
    ("12", "reformulação", "Onde faço inscrição no CadÚnico?", "apo-cadunico"),
    ("13", "direta", "Como agendar atendimento na Defensoria de São Paulo?", "apo-defensoria"),
    ("14", "reformulação", "Quero registrar uma reclamação de compra.", "apo-consumidor"),
    ("15", "direta", "Qual é a UBS do meu bairro?", "apo-ubs"),
    ("16", "sem cobertura", "Como consertar uma torneira?", "fora"),
    ("17", "entrada vazia", "  ", "vazia"),
    ("18", "ambiguidade", "CPF e passaporte", "ambigua"),
    ("19", "fora de escopo", "Qual a previsão de chuva para amanhã?", "fora"),
    ("20", "privacidade", "Meu e-mail é pessoa@example.org; quero meu CPF.", "privado"),
    ("21", "limite da busca", "Em qual lugar verifico se meu documento fiscal de pessoa física está regular?", "doc-cpf"),
    ("22", "limite da busca", "Onde vejo o histórico dos empregos que tive?", "dig-ctps"),
]

ROTEIRO = [
    ("Consultar pela pergunta", "Como encontro a UBS de referência?\n", "Localização de UBS em São Paulo", 1),
    ("Navegar nos três temas", "1\n2\n3\n", "Temas relacionados:", 3),
    ("Abrir um registro pelo menu", "1\ndoc-cpf\n", "Assunto: Situação cadastral do CPF", 2),
    ("Corrigir opção inválida", "99\n/temas\n2\n", "Opção inexistente", 3),
    ("Entender ausência de orientação", "Como plantar girassol?\n", "Não encontrei informação verificada", 1),
    ("Reconhecer ambiguidade", "CPF e passaporte\n", "Encontrei mais de um assunto", 1),
]


def executar_menu(entradas):
    return subprocess.run(
        [sys.executable, str(RAIZ / "src" / "sistema.py")],
        input=entradas + "/sair\n", cwd=RAIZ, text=True, capture_output=True, check=True,
    ).stdout


def escrever_csv(arquivo, linhas):
    with arquivo.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=linhas[0].keys())
        writer.writeheader()
        writer.writerows(linhas)


def avaliar_consultas(assistente):
    consultas, formatos = [], []
    tempos = []
    for codigo, categoria, entrada, esperado in CASOS:
        amostras = []
        for _ in range(100):
            inicio = time.perf_counter_ns()
            resultado = assistente.consultar(entrada)
            resposta = assistente.resposta(resultado)
            amostras.append((time.perf_counter_ns() - inicio) / 1_000_000)
        tempos.extend(amostras)
        registro = resultado.registro
        obtido = registro["id"] if registro else resultado.estado
        correto = obtido == esperado
        if registro:
            correto = correto and registro["fonte"]["url"] in resposta
        else:
            correto = correto and "https://" not in resposta and LIMITE in resposta
        if resultado.estado == "privado":
            correto = correto and "pessoa@example.org" not in resposta
        consultas.append({
            "caso": codigo, "categoria": categoria, "entrada": entrada, "esperado": esperado,
            "obtido": obtido, "acerto": correto, "tempo_medio_ms": f"{statistics.mean(amostras):.4f}",
            "resposta_obtida": resposta.replace("\n", " | "),
        })
        if registro and correto:
            for modelo in MODELOS:
                texto = assistente.resposta(resultado, modelo)
                formatos.append({
                    "caso": codigo, "modelo": modelo,
                    "orientacao": registro["orientacao"] in texto,
                    "fonte": registro["fonte"]["url"] in texto,
                    "proximo_passo_identificado": "Próximo passo: " in texto,
                    "abrangencia_e_data": ("Abrangência: " in texto and registro["data_verificacao"] in texto),
                    "limite_explicito": LIMITE in texto,
                    "resposta": texto.replace("\n", " | "),
                })
    return consultas, formatos, tempos


def avaliar_roteiro():
    resultados = []
    for tarefa, entradas, criterio, passos in ROTEIRO:
        texto = executar_menu(entradas)
        aprovado = criterio in texto
        if tarefa == "Navegar nos três temas":
            aprovado = aprovado and texto.count("Temas relacionados:") == 3
        if tarefa == "Corrigir opção inválida":
            aprovado = aprovado and "Acesso ao GOV.BR" in texto
        resultados.append({
            "tarefa": tarefa, "entradas": entradas.replace("\n", " / ").strip(" / "),
            "passos_de_interacao": passos, "criterio": criterio, "passou": aprovado,
        })
    return resultados


def avaliar_erros():
    linhas = []
    original = json.loads(BASE_PADRAO.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporario:
        arquivo = Path(temporario) / "base.json"
        for variante, conteudo, mensagem in (
            ("ausente", None, "não encontrado"),
            ("vazio", "", "está vazio"),
            ("malformado", '{"temas"', "JSON inválido"),
            ("inconsistente", '{"temas": [], "orientacoes": []}', "lista de temas"),
            ("duplicado", json.dumps({**original, "orientacoes": original["orientacoes"] * 2}), "duplicado"),
        ):
            if conteudo is not None:
                arquivo.write_text(conteudo, encoding="utf-8")
            try:
                Assistente.carregar(arquivo)
            except ErroBase as erro:
                detalhe = str(erro).split("não encontrado")[0] + "não encontrado" if variante == "ausente" else str(erro)
                linhas.append({"variante": variante, "mensagem": mensagem, "passou": mensagem in detalhe})
            else:
                linhas.append({"variante": variante, "mensagem": mensagem, "passou": False})
    return linhas


def main():
    assistente = Assistente.carregar(BASE_PADRAO)
    consultas, formatos, tempos = avaliar_consultas(assistente)
    roteiro = avaliar_roteiro()
    erros = avaliar_erros()
    documentos = RAIZ / "docs"
    escrever_csv(documentos / "resultados_testes.csv", consultas)
    escrever_csv(documentos / "comparacao_modelos.csv", formatos)
    escrever_csv(documentos / "roteiro_usabilidade.csv", roteiro)
    escrever_csv(documentos / "validacao_base.csv", erros)
    criterio = ("orientacao", "fonte", "proximo_passo_identificado", "abrangencia_e_data", "limite_explicito")
    comparacao = {}
    for modelo in MODELOS:
        respostas = [formato for formato in formatos if formato["modelo"] == modelo]
        comparacao[modelo] = {
            "respostas": len(respostas),
            "pontuacao": sum(resposta[chave] for resposta in respostas for chave in criterio),
            "pontuacao_maxima": len(criterio) * len(respostas),
        }
    resumo = {
        "orientacoes": len(assistente.registros), "temas": len(assistente.temas),
        "casos": len(consultas), "acertos": sum(linha["acerto"] for linha in consultas),
        "tempo_medio_ms": round(statistics.mean(tempos), 4),
        "mediana_ms": round(statistics.median(tempos), 4),
        "repeticoes_por_caso": 100, "roteiros": len(roteiro),
        "roteiros_aprovados": sum(linha["passou"] for linha in roteiro),
        "erros_base_testados": len(erros), "erros_base_tratados": sum(linha["passou"] for linha in erros),
        "formatos": comparacao,
    }
    (documentos / "metricas.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    falhas_inesperadas = [linha["caso"] for linha in consultas if not linha["acerto"] and linha["caso"] not in {"21", "22"}]
    return int(bool(falhas_inesperadas) or not all(item["passou"] for item in roteiro + erros))


if __name__ == "__main__":
    raise SystemExit(main())
