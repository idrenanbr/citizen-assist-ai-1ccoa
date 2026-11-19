"""Assistente textual de orientação cidadã com base local verificável."""

import argparse
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urlsplit

BASE_PADRAO = Path(__file__).resolve().parents[1] / "data" / "base.json"
LIMITE = "Protótipo informativo. Confirme documentos, horários e condições no canal oficial."
DADO_PESSOAL = re.compile(
    r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|(?<!\w)\d{3}[. ]?\d{3}[. ]?\d{3}[- ]?\d{2}(?!\w)"
    r"|(?<!\w)(?:\+55\s*)?\(?\d{2}\)?[ -]?\d{4,5}[- ]?\d{4}(?!\w)",
    re.IGNORECASE,
)
MODELOS = {
    "A": {
        "instrucao": "Responda com a orientação verificada e indique o órgão e o link.",
        "campos": (
            "Orientação: {orientacao}",
            "Fonte: {orgao} | {url}",
        ),
    },
    "B": {
        "instrucao": (
            "Organize a orientação em blocos: assunto, próximo passo, fonte, "
            "data e abrangência. Termine indicando o limite do protótipo."
        ),
        "campos": (
            "Assunto: {titulo}",
            "Próximo passo: {orientacao}",
            "Fonte: {orgao}",
            "{url}",
            "Verificação: {data_verificacao} | Abrangência: {abrangencia}",
            "Limite: " + LIMITE,
        ),
    },
}

CAMPOS_REGISTRO = (
    "id", "tema", "subtema", "titulo", "pergunta", "orientacao", "abrangencia", "data_verificacao"
)


class ErroBase(ValueError):
    """Problema de leitura, conteúdo ou estrutura da base local."""


def normalizar(texto):
    """Reduz diferenças de acento, caixa e pontuação para a busca."""
    sem_acentos = "".join(
        caractere for caractere in unicodedata.normalize("NFKD", texto.casefold())
        if not unicodedata.combining(caractere)
    )
    return " ".join(re.findall(r"[a-z0-9]+", sem_acentos))


def textos_validos(*valores):
    return all(isinstance(valor, str) and bool(valor.strip()) for valor in valores)


def coletar_temas(temas):
    if not isinstance(temas, list) or not temas:
        raise ErroBase("A base precisa de uma lista de temas.")
    indice = {}
    for tema in temas:
        if not isinstance(tema, dict) or not textos_validos(tema.get("id"), tema.get("nome")):
            raise ErroBase("Há um tema sem identificador ou nome.")
        codigo = tema["id"]
        subtemas = tema.get("subtemas")
        relacionados = tema.get("relacionados")
        if codigo in indice:
            raise ErroBase(f"Tema duplicado: {codigo}.")
        if not isinstance(subtemas, dict) or not subtemas or not textos_validos(*subtemas.values()):
            raise ErroBase(f"Tema sem subtemas válidos: {codigo}.")
        if not isinstance(relacionados, list) or not textos_validos(*relacionados):
            raise ErroBase(f"Relações inválidas no tema {codigo}.")
        indice[codigo] = tema

    for codigo, tema in indice.items():
        relacoes = tema["relacionados"]
        if any(rel == codigo or rel not in indice for rel in relacoes) or len(set(relacoes)) != len(relacoes):
            raise ErroBase(f"Relação inconsistente no tema {codigo}.")
    return indice


def validar_registro(registro, temas):
    if not isinstance(registro, dict) or not textos_validos(*(registro.get(campo) for campo in CAMPOS_REGISTRO)):
        raise ErroBase("Há uma orientação sem campos essenciais.")
    codigo = registro["id"]
    tema = temas.get(registro["tema"])
    if tema is None or registro["subtema"] not in tema["subtemas"]:
        raise ErroBase(f"Tema ou subtema desconhecido na orientação {codigo}.")

    palavras = registro.get("palavras_chave")
    if not isinstance(palavras, list) or not palavras or not textos_validos(*palavras):
        raise ErroBase(f"Palavras-chave inválidas na orientação {codigo}.")
    if any(not normalizar(palavra) for palavra in palavras):
        raise ErroBase(f"Palavra-chave sem caracteres pesquisáveis na orientação {codigo}.")

    fonte = registro.get("fonte")
    if not isinstance(fonte, dict) or not textos_validos(fonte.get("orgao"), fonte.get("url")):
        raise ErroBase(f"Fonte incompleta na orientação {codigo}.")
    try:
        url = urlsplit(fonte["url"])
        if url.scheme != "https" or not url.hostname or url.username is not None or url.password is not None:
            raise ValueError("link inválido")
        if date.fromisoformat(registro["data_verificacao"]).isoformat() != registro["data_verificacao"]:
            raise ValueError("data fora do formato ISO")
    except ValueError as erro:
        raise ErroBase(f"URL ou data inválida na orientação {codigo}.") from erro


@dataclass(frozen=True)
class Resultado:
    estado: str
    registro: dict | None = None
    candidatos: tuple = ()


class Assistente:
    def __init__(self, temas, registros):
        self.temas = temas
        self.registros = registros
        self.por_tema = {tema: [] for tema in temas}
        self.aliases = {}
        for codigo, registro in registros.items():
            self.por_tema[registro["tema"]].append(registro)
            termos = registro["palavras_chave"] + [registro["pergunta"], registro["titulo"], codigo]
            self.aliases[codigo] = tuple(dict.fromkeys(normalizar(termo) for termo in termos))

    @classmethod
    def carregar(cls, caminho):
        try:
            conteudo = caminho.read_text(encoding="utf-8")
        except FileNotFoundError as erro:
            raise ErroBase(f"Arquivo de orientações não encontrado: {caminho}.") from erro
        except (OSError, UnicodeError) as erro:
            raise ErroBase("Não foi possível ler o arquivo como texto UTF-8.") from erro

        if not conteudo.strip():
            raise ErroBase("O arquivo de orientações está vazio.")
        try:
            dados = json.loads(conteudo)
        except json.JSONDecodeError as erro:
            raise ErroBase(f"JSON inválido na linha {erro.lineno}, coluna {erro.colno}.") from erro
        if not isinstance(dados, dict):
            raise ErroBase("O JSON precisa conter um objeto com temas e orientações.")
        temas = coletar_temas(dados.get("temas"))
        linhas = dados.get("orientacoes")
        if not isinstance(linhas, list) or not linhas:
            raise ErroBase("A base não contém orientações.")

        registros = {}
        for registro in linhas:
            validar_registro(registro, temas)
            codigo = registro["id"]
            if codigo in registros:
                raise ErroBase(f"Identificador de orientação duplicado: {codigo}.")
            registros[codigo] = registro
        return cls(temas, registros)

    def consultar(self, pergunta, tema=None):
        if DADO_PESSOAL.search(pergunta):
            return Resultado("privado")
        if len(pergunta) > 500:
            return Resultado("longa")
        chave = normalizar(pergunta)
        if not chave:
            return Resultado("vazia")

        busca = f" {chave} "
        registros = self.por_tema[tema] if tema else self.registros.values()
        candidatos = []
        for registro in registros:
            termos = self.aliases[registro["id"]]
            # Frases mais específicas prevalecem. Um sinônimo conta apenas uma vez.
            nota = max(
                (100 if chave == termo else 4 * len(termo.split()) + 1
                 for termo in termos if f" {termo} " in busca),
                default=0,
            )
            if nota:
                candidatos.append((nota, registro))

        if not candidatos:
            return Resultado("fora")
        candidatos.sort(key=lambda entrada: (-entrada[0], entrada[1]["id"]))
        melhores = tuple(registro for nota, registro in candidatos if nota == candidatos[0][0])
        if len(melhores) > 1:
            return Resultado("ambigua", candidatos=melhores)
        return Resultado("encontrada", registro=melhores[0])

    def relacionados(self, tema):
        codigos = self.temas[tema]["relacionados"] if tema else self.temas
        return [self.temas[codigo]["nome"] for codigo in codigos]

    def resposta(self, resultado, modelo="B", tema=None):
        if resultado.estado == "encontrada":
            registro = resultado.registro
            valores = {**registro, **registro["fonte"]}
            return "\n".join(campo.format_map(valores) for campo in MODELOS[modelo]["campos"])

        if resultado.estado == "ambigua":
            titulos = "; ".join(item["titulo"] for item in resultado.candidatos)
            mensagem = f"Encontrei mais de um assunto: {titulos}. Qual você quer consultar?"
        else:
            mensagens = {
                "vazia": "Digite uma pergunta ou selecione um tema.",
                "fora": "Não encontrei informação verificada para essa pergunta.",
                "privado": "Digite somente o assunto, sem CPF, e-mail ou telefone.",
                "longa": "Resuma o assunto em até 500 caracteres.",
            }
            mensagem = mensagens[resultado.estado]
        temas = " | ".join(self.relacionados(tema))
        return f"{mensagem}\nTemas para continuar: {temas}\n{LIMITE}"


def mostrar_temas(assistente):
    for numero, tema in enumerate(assistente.temas.values(), start=1):
        print(f"{numero}. {tema['nome']}")


def mostrar_submenu(assistente, tema):
    dados = assistente.temas[tema]
    print(f"\n{dados['nome']}")
    for subtema, nome in dados["subtemas"].items():
        print(f"  {nome}")
        for registro in assistente.por_tema[tema]:
            if registro["subtema"] == subtema:
                print(f"    {registro['id']}  {registro['titulo']}")
    print("Temas relacionados: " + " | ".join(assistente.relacionados(tema)))
    print("Use /temas para mudar de assunto.")


def iniciar_menu(assistente, modelo):
    """Permite combinar navegação por tema, atalhos e perguntas em texto."""
    print("Citizen Assist AI | Orientação cidadã")
    print(LIMITE)
    print("Digite sua pergunta ou o número de um tema. Comandos: /temas, /sair.")
    mostrar_temas(assistente)
    tema = None
    temas = tuple(assistente.temas)
    while True:
        entrada = input("\nConsulta > ").strip()
        if entrada.casefold() == "/sair":
            return
        if entrada.casefold() == "/temas":
            tema = None
            mostrar_temas(assistente)
            continue

        if entrada.isascii() and entrada.isdigit() and len(entrada) <= 2:
            numero = int(entrada)
            if 1 <= numero <= len(temas):
                tema = temas[numero - 1]
                mostrar_submenu(assistente, tema)
            else:
                print("Opção inexistente. Consulte /temas para ver as opções.")
            continue

        resultado = assistente.consultar(entrada, tema)
        print(assistente.resposta(resultado, modelo, tema))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=BASE_PADRAO, help="Caminho da base JSON.")
    parser.add_argument("--modelo", choices=MODELOS, default="B", help="Formato de resposta.")
    parser.add_argument("--pergunta", help="Executa uma consulta sem abrir o menu.")
    argumentos = parser.parse_args(argv)
    try:
        assistente = Assistente.carregar(argumentos.base)
    except ErroBase as erro:
        print(f"Erro na base: {erro}", file=sys.stderr)
        return 2

    if argumentos.pergunta is not None:
        resultado = assistente.consultar(argumentos.pergunta)
        print(assistente.resposta(resultado, argumentos.modelo))
    else:
        try:
            iniciar_menu(assistente, argumentos.modelo)
        except (EOFError, KeyboardInterrupt):
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
