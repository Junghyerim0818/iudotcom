import os
import shutil
import datetime
from pathlib import Path

def organize_images(base_path):
    # 이미지 파일 확장자 목록
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.raw', '.cr2', '.nef'}
    
    base_dir = Path(base_path)
    if not base_dir.exists():
        print(f"경로를 찾을 수 없습니다: {base_path}")
        return

    # 모든 파일 수집
    files_to_process = []
    print("파일 검색 중...")
    
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() in IMAGE_EXTENSIONS:
                files_to_process.append(file_path)

    print(f"총 {len(files_to_process)}개의 이미지 파일을 찾았습니다.")

    for src_path in files_to_process:
        try:
            # 수정 날짜 가져오기
            mtime = os.path.getmtime(src_path)
            dt = datetime.datetime.fromtimestamp(mtime)
            
            # 년도별 폴더 경로
            year_folder = base_dir / str(dt.year)
            
            # 새 파일 이름 생성 (YYYY-MM-DD_HH-MM-SS)
            new_filename_base = dt.strftime("%Y-%m-%d_%H-%M-%S")
            extension = src_path.suffix.lower()
            new_filename = f"{new_filename_base}{extension}"
            
            # 대상 경로 설정
            if not year_folder.exists():
                year_folder.mkdir(parents=True, exist_ok=True)
                
            dest_path = year_folder / new_filename
            
            # 파일 이름 중복 처리
            counter = 1
            while dest_path.exists():
                # 이미 같은 파일인지 확인 (경로가 같으면 건너뜀)
                if src_path.resolve() == dest_path.resolve():
                    break
                
                # 이름 뒤에 인덱스 추가
                new_filename = f"{new_filename_base}_{counter}{extension}"
                dest_path = year_folder / new_filename
                counter += 1
            
            # 파일 이동 (같은 경로가 아닐 때만)
            if src_path.resolve() != dest_path.resolve():
                print(f"이동: {src_path.name} -> {year_folder.name}\\{dest_path.name}")
                shutil.move(str(src_path), str(dest_path))
                
        except Exception as e:
            print(f"오류 발생 ({src_path.name}): {e}")

    # 빈 폴더 정리 (선택 사항)
    for root, dirs, files in os.walk(base_dir, topdown=False):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            # 년도 폴더인 경우 건너뛰기 (숫자로만 구성된 4자리)
            if dir_path.name.isdigit() and len(dir_path.name) == 4:
                continue
            try:
                if not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    print(f"빈 폴더 삭제: {dir_path}")
            except Exception:
                pass

if __name__ == "__main__":
    target_path = r"C:\Users\xktkd\Desktop\images"
    organize_images(target_path)


