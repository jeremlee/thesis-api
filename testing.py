from transformers import BitsAndBytesConfig, AutoModelForCausalLM, AutoTokenizer, pipeline

import torch
import PyPDF2
import time
from datetime import datetime

localized_parsing_prompt = """
Parse this resume into structured JSON:
name, education, skills, experience
"""


def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        text = ""

        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)

            for page in reader.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"

        extracted_text = text.strip()

        if not extracted_text:
            raise Exception(
                "No text could be extracted from the PDF. It may be image-based."
            )

        return extracted_text

    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")


# ----------------------------
# Quantization Config
# ----------------------------
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.float16,
    llm_int8_enable_fp32_cpu_offload=True
)


# ----------------------------
# Load Gemma 3 1B Instruct
# ----------------------------
local_model_path = r"D:/Documents/A_College/alliance thesis/ai_api/gemma-3-1b-it"

tokenizer = AutoTokenizer.from_pretrained(local_model_path)

model = AutoModelForCausalLM.from_pretrained(
    local_model_path,
    quantization_config=quant_config,
    device_map="auto"
)

gemma_pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    temperature=0.0,
    do_sample=False
)
print("CUDA Available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU Name:", torch.cuda.get_device_name(0))

print("Model Device:", model.device)


# ----------------------------
# Main
# ----------------------------
print("CUDA Available:", torch.cuda.is_available())

pdf_path = "resumes/7.pdf"
extracted_text = extract_text_from_pdf(pdf_path)

prompt = localized_parsing_prompt + "\n\n" + extracted_text

start_time = time.time()
start_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

out = gemma_pipe(
    prompt,
    max_new_tokens=1500
)

end_time = time.time()
end_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
elapsed_time = end_time - start_time

generated_text = out[0]["generated_text"]

print(f"Time taken: {elapsed_time:.2f} seconds")
print(generated_text)


# ----------------------------
# Save Output
# ----------------------------
with open("resume_output_1.txt", "w", encoding="utf-8") as f:
    f.write(f"Start Time: {start_dt}\n")
    f.write(f"End Time: {end_dt}\n")
    f.write(f"Elapsed Time: {elapsed_time:.2f} seconds\n\n")

    f.write("=== Extracted Resume Text ===\n")
    f.write(extracted_text)
    f.write("\n\n")

    f.write("=== Generated Output ===\n")
    f.write(generated_text)

print("Output and timing written to resume_output_1.txt")