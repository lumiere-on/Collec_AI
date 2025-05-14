from io import BytesIO
import requests


from PIL import Image
from pydantic import BaseModel
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from model.tag import get_tags_from_azure, classify_tags
from model.ui import detect_ui
from model.ocr import detect_text, classify_text


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],  
)
class ImageURL(BaseModel):
    url: str

class annotateResponse(BaseModel):
    category: str
    tags: list[str]
    caption : list[str]
    

@app.post("/ai/annotate", response_model=annotateResponse)
def annotate_image(image_data: ImageURL): 
# def annotate_image(image_data: UploadFile = File(...)): 
    try:
        # URL에서 이미지 다운로드
        response = requests.get(image_data.url)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail="이미지 URL에서 이미지를 가져올 수 없습니다") from e

    try:
        # 다운로드한 바이너리 데이터를 PIL 이미지로 변환
        image = Image.open(BytesIO(response.content))
        image = image.copy()
        image = image.convert('RGB')
    except Exception as e:
        raise HTTPException(status_code=401, detail="유효하지 않은 이미지 파일입니다") from e



    # Azure tagging
    tags = get_tags_from_azure(image)
    
    # extract str from tags for caption
    tags_str = ",".join(tags)
    
    # Google OCR
    extracted_text = detect_text(image)  
   
    category = classify_tags(tags)  # Step 1: Azure tagging 기반
    if category == "기타":
        category = detect_ui(image)  # Step 2: Roboflow UI Detection 기반
        if category == "기타":
            category = classify_text(extracted_text)  # Step 3: Google OCR 기반

    caption = [category, tags_str, extracted_text]
    
    
    return annotateResponse(
        category=category,
        tags=tags,
        caption=caption 
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=13131)
    
    
