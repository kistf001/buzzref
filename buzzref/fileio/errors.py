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


IMG_LOADING_ERROR_MSG = (
    'Unknown format or too big?\n'
    'Check Settings -> Images & Items -> Maximum Image Size')


class BuzzFileIOError(Exception):
    def __init__(self, msg, filename):
        self.msg = msg
        self.filename = filename
