import base64
import anthropic
from dotenv import load_dotenv

from schemas.parties import Parties
from schemas.terms import Term


load_dotenv()


def load_pdf(path: str) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def iter_uncited_paths(data, cited_text: str, path: str = ""):
    """Yield (path, value) for every leaf value not found in cited text."""
    if isinstance(data, dict):
        for key, value in data.items():
            yield from iter_uncited_paths(
                value, cited_text, f"{path}.{key}" if path else key
            )
    elif isinstance(data, list):
        for i, item in enumerate(data):
            yield from iter_uncited_paths(item, cited_text, f"{path}[{i}]")
    elif isinstance(data, (str, int, float)) and str(data) not in cited_text:
        yield path, data


tools = [
    {
        "name": "extract_parties",
        "description": "Extract the contracting parties from the agreement.",
        "input_schema": Parties.model_json_schema(),
    },
    {
        "name": "extract_terms",
        "description": "Extract the term details from the agreement.",
        "input_schema": Term.model_json_schema(),
    },
]

TOOL_MODELS = {
    "extract_parties": Parties,
    "extract_terms": Term,
}


def main(pdf_path: str):
    pdf_base64 = load_pdf(pdf_path)
    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        tools=tools,
        tool_choice={"type": "auto"},
        system="You MUST quote the relevant document passages before calling any extraction tool. Always provide cited text first, then the tool call.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64,
                        },
                        "citations": {"enabled": True},
                    },
                    {
                        "type": "text",
                        "text": "Extract all contract terms from this document. For each section you extract, first quote the relevant passages from the document, then call the appropriate extraction tool with the structured data. Use only the tools provided.",
                    },
                ],
            }
        ],
    )

    citations = []
    tool_calls = []

    for block in response.content:
        if block.type == "text" and block.citations:
            citations.extend(block.citations)
        elif block.type == "tool_use":
            tool_calls.append(block)

    for tool_call in tool_calls:
        validated = TOOL_MODELS[tool_call.name](**tool_call.input)
        print(f"{tool_call.name}")
        print(validated, "\n")

    cited_texts = [c.cited_text for c in citations]
    full_cited = "\n\n".join(cited_texts)

    for tool_call in tool_calls:
        for path, value in iter_uncited_paths(tool_call.input, full_cited):
            print(
                f"WARNING, this information may need manual review: {tool_call.name} — {path}: '{value}'"
            )


if __name__ == "__main__":
    ## Test with mock contract
    main("contract_examples/contract_one.pdf")
