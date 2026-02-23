# This file is part of BuzzRef.
#
# BuzzRef is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BuzzRef is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BuzzRef.  If not, see <https://www.gnu.org/licenses/>.

"""Translation files for BuzzRef.

This package contains .qm (compiled) and .ts (source) translation files
for internationalization support.

Supported languages:
- ko (Korean / 한국어)

To add a new language:
1. Create buzzref_{lang}.ts file (copy from buzzref_ko.ts)
2. Translate strings in the .ts file
3. Compile: pyside6-lrelease buzzref_{lang}.ts -qm buzzref_{lang}.qm
"""

import os

TRANSLATIONS_PATH = os.path.dirname(__file__)
