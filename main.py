import base64
import anthropic
from dotenv import load_dotenv
from models.schemas import Parties

load_dotenv()


def load_pdf(path: str) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


tools = [
    {
        "name": "extract_parties",
        "description": "Extract the contracting parties from the agreement.",
        "input_schema": Parties.model_json_schema(),
    }
]


def main(pdf_path: str):
    pdf_base64 = load_pdf(pdf_path)
    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        tools=tools,
        tool_choice={"type": "auto"},
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
                        "text": "Extract all contract terms from this document. For each section you extract, first quote the relevant passages from the document, then call the appropriate extraction tool with the structured data.",
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

    print(citations)
    print(tool_calls)

    for tool_call in tool_calls:
        validated = Parties(**tool_call.input)

    cited_texts = [c.cited_text for c in citations]
    full_cited = "\n\n".join(cited_texts)

    provider_name = validated.provider.company_name
    customer_name = validated.customer.company_name

    if provider_name not in full_cited:
        print(f"WARNING: '{provider_name}' not found in cited text")

    if customer_name not in full_cited:
        print(f"WARNING: '{customer_name}' not found in cited text")

    print(validated)


if __name__ == "__main__":
    main("contract_examples/contract_one.pdf")
