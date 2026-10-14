
# LocalPhoto Studio

RTX GPU 가속 및 로컬 AI 기반 사진 편집 프로그램

## 개발 환경
- Windows 11
- Python 3.12.8
- PySide6
- NVIDIA RTX 5070 Ti

## 현재 구현 기능
- JPG, PNG 등 이미지 불러오기
- 이미지 미리보기
- 창 크기에 따른 이미지 자동 조절
- 파일명 및 해상도 표시

## 실행 방법

1. Python 가상환경 생성
   python -m venv .venv

2. 패키지 설치
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt

3. 프로그램 실행
   .\.venv\Scripts\python.exe main.py

## 향후 개발
- 이미지 색상 보정
- GPU 기반 이미지 처리
- 비파괴 편집 및 레이어
- AI 인물 보정
- AI 노이즈 제거
- AI 배경 제거

## 상태
초기 개발 단계
