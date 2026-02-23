#!/usr/bin/env python3
"""
BuzzRef Translation Compiler
===========================

Qt 번역 파일(.ts)을 바이너리 파일(.qm)로 컴파일합니다.
QTranslator는 .qm 파일만 로드할 수 있으므로, 앱 실행 전에 컴파일이 필요합니다.

파일 형식
---------
- .ts : XML 소스 파일 (번역자가 편집)
- .qm : 컴파일된 바이너리 (앱에서 로드)

디렉토리 구조
------------
buzzref/translations/
├── __init__.py          # 패키지 초기화
├── buzzref_ko.ts         # 한국어 소스 파일
├── buzzref_ko.qm         # 한국어 컴파일 파일 (자동 생성)
├── buzzref_ja.ts         # 일본어 소스 파일 (추가 예정)
└── buzzref_ja.qm         # 일본어 컴파일 파일 (자동 생성)

사용법
------

1. 기본 사용법 (모든 .ts 파일 컴파일):

    python scripts/compile_translations.py

2. 개별 파일 컴파일:

    pyside6-lrelease buzzref/translations/buzzref_ko.ts

의존성 설치
-----------

이 스크립트는 lrelease 도구가 필요합니다.

방법 1 - pip (권장):
    pip install pyside6-essentials

방법 2 - 시스템 패키지 (Debian/Ubuntu):
    sudo apt install qt6-tools-dev-tools

새 언어 추가하기
----------------

1. 기존 .ts 파일 복사:
    cp buzzref/translations/buzzref_ko.ts buzzref/translations/buzzref_ja.ts

2. 파일 상단의 language 속성 수정:
    <TS version="2.1" language="ja_JP">

3. <translation> 태그 내용 번역:
    <source>&amp;Open</source>
    <translation>開く(&amp;O)</translation>

4. 컴파일:
    python scripts/compile_translations.py

5. 테스트:
    LANG=ja_JP.UTF-8 python -m buzzref

번역 업데이트하기
-----------------

1. .ts 파일 직접 편집 (XML 형식)
2. 또는 Qt Linguist 사용 (GUI 도구):
    linguist buzzref/translations/buzzref_ko.ts

3. 변경 후 재컴파일:
    python scripts/compile_translations.py

번역 테스트
-----------

특정 언어로 앱 실행:
    LANG=ko_KR.UTF-8 python -m buzzref

로그에서 번역 로드 확인:
    INFO __main__: Loaded translation for locale: ko_KR

주의사항
--------

- .qm 파일은 Git에 커밋해야 합니다 (배포 패키지에 포함)
- .ts 파일 수정 후 반드시 재컴파일 필요
- 새 문자열 추가 시 모든 .ts 파일에 추가해야 함

Context 설명
------------

Actions : 메뉴 액션 (열기, 저장, 복사 등)
Menu    : 메뉴 이름 (파일, 편집, 보기 등)

개발자 가이드: 새 기능 추가 시 i18n 처리
--------------------------------------

1. QObject 서브클래스 내부:
   - self.tr('English text') 사용

2. QObject 외부 (모듈 레벨):
   - from buzzref.i18n import _tr
   - _tr('Context', 'English text') 사용

3. 새 Action 추가 시:
   a) buzzref/actions/actions.py에 Action 추가:
      Action(id='my_action', text='&My Action', ...)

   b) buzzref/translations/*.ts 파일에 문자열 추가:
      <message>
          <source>&amp;My Action</source>
          <translation>내 액션(&amp;M)</translation>
      </message>

   c) 재컴파일: python scripts/compile_translations.py

4. 새 메뉴 추가 시:
   a) buzzref/actions/menu_structure.py에 메뉴 추가
   b) buzzref/translations/*.ts의 Menu context에 추가

5. 다이얼로그/위젯 텍스트:
   a) QObject 내부면 self.tr() 사용
   b) 외부면 _tr('ClassName', 'text') 사용
   c) .ts 파일에 수동 추가 필요

번역 작업 흐름
--------------

[코드 수정] -> [.ts 수동 업데이트] -> [컴파일] -> [테스트]
                    ↓
            번역자에게 .ts 파일 전달
                    ↓
            번역 완료 후 PR

문제 해결
---------

Q: lrelease를 찾을 수 없음
A: pip install pyside6-essentials 실행

Q: 번역이 적용되지 않음
A: 1) .qm 파일이 있는지 확인
   2) LANG 환경변수 확인 (LANG=ko_KR.UTF-8)
   3) 로그에서 "Loaded translation" 메시지 확인

Q: 새 액션/메뉴가 번역되지 않음
A: 1) buzzref/actions/actions.py에 추가된 텍스트를
   2) buzzref/translations/*.ts 파일에 수동 추가
   3) 재컴파일

"""

import subprocess
import sys
from pathlib import Path


def find_lrelease():
    """Find lrelease executable."""
    candidates = [
        'pyside6-lrelease',  # pip install pyside6-essentials (recommended)
        'lrelease',
        'lrelease6',
        '/usr/lib/qt6/bin/lrelease',
    ]

    for cmd in candidates:
        try:
            # Use -help instead of --version (pyside6-lrelease doesn't support --version)
            result = subprocess.run(
                [cmd, '-help'],
                capture_output=True,
                text=True
            )
            # If command exists and shows help, it's valid
            if 'lrelease' in result.stdout.lower() or 'lrelease' in result.stderr.lower():
                return cmd
        except FileNotFoundError:
            continue

    return None


def compile_translations():
    """Compile all .ts files to .qm."""
    translations_dir = Path(__file__).parent.parent / 'buzzref' / 'translations'
    ts_files = list(translations_dir.glob('*.ts'))

    if not ts_files:
        print("No .ts files found in:", translations_dir)
        return 1

    lrelease = find_lrelease()
    if not lrelease:
        print("ERROR: lrelease not found.")
        print()
        print("Install one of:")
        print("  pip install pyside6-essentials    (recommended)")
        print("  apt install qt6-tools-dev-tools   (system)")
        return 1

    print(f"Using: {lrelease}")
    print(f"Directory: {translations_dir}")
    print()

    success_count = 0
    for ts_file in ts_files:
        qm_file = ts_file.with_suffix('.qm')
        print(f"Compiling: {ts_file.name}")

        result = subprocess.run(
            [lrelease, str(ts_file), '-qm', str(qm_file)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"  ERROR: {result.stderr}")
            return 1

        # Parse lrelease output for translation count
        if result.stdout:
            print(f"  {result.stdout.strip()}")
        print(f"  Output: {qm_file.name}")
        success_count += 1

    print()
    print(f"Done! Compiled {success_count} file(s).")
    return 0


if __name__ == '__main__':
    sys.exit(compile_translations())
