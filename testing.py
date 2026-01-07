from transformers import BitsAndBytesConfig, AutoModelForCausalLM, AutoTokenizer, pipeline
from app.dependencies import localized_parsing_prompt
import torch
import PyPDF2
import time
from datetime import datetime


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
                "No text could be extracted from the PDF. It might be image-based."
            )

        return extracted_text

    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.float16,
    llm_int8_enable_fp32_cpu_offload=True  
)

local_model_path = "D:/Documents/A_College/alliance thesis/ai_api/gemma-3-4b-it"

tokenizer = AutoTokenizer.from_pretrained(local_model_path)

model = AutoModelForCausalLM.from_pretrained(
    local_model_path,
    quantization_config=quant_config, 
    device_map={"": "cpu"}              
)


falcon_pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    temperature=0.0,
    do_sample=False
)


print(torch.cuda.is_available())
extracted_text = extract_text_from_pdf("resumes/7.pdf")
prompt = localized_parsing_prompt + "\n" + extracted_text
start_time = time.time()
start_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
out = falcon_pipe(
    prompt,
    max_new_tokens=1500,
    temperature=0.0,
    do_sample=False
)
end_time = time.time()
end_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
elapsed_time = end_time - start_time

print(f"Time taken: {elapsed_time:.2f} seconds")
end_time = time.time()
elapsed_time = end_time - start_time
generated_text = out[0]["generated_text"]
print(f"Time taken: {elapsed_time:.2f} seconds")
with open("resume_output_1.txt", "w", encoding="utf-8") as f:
    f.write(f"Start Time: {start_dt}\n")
    f.write(f"End Time: {end_dt}\n")
    f.write(f"Elapsed Time: {elapsed_time:.2f} seconds\n\n")
    f.write("\nExtracted text from resume:\n")
    f.write(extracted_text)
    f.write("Generated Text:\n")
    f.write(generated_text)

print("Output and timing written")