import os
import platform
import pytest
import stat
import sys
from zipfile import ZipFile

from chromeguard import Guard
from chromeguard import linux
from chromeguard.linux import LINUX_FILENAME, linux_get_path
from chromeguard.mac import MAC_FILENAME
from chromeguard.win import WIN_FILENAME, get_local_release, win_get_path
from chromeguard.exceptions import NotUpdatedException
from chromeguard.utils import API_get_latest_release, unzip


APPVEYOR_PATH = 'C:\\Tools\\WebDriver'
TESTS_FOLDER = os.path.join(os.getcwd(), 'tests')
PLATFORM = platform.system()
TEST_RELEASE = '2.21'


def clean_up(executable):
    while True:
        try:
            os.remove(executable)
            while os.path.isfile(executable) is True:
                pass
        except PermissionError:
            pass
        else:
            break


@pytest.fixture(scope='session')
def installation_file():
    if sys.platform == 'win32':
        installation_file = os.path.join(TESTS_FOLDER, WIN_FILENAME)
        #executable = os.path.join(TMP_PATH_FOLDER, 'chromedriver.exe')
    elif sys.platform == 'linux':
        installation_file = os.path.join(TESTS_FOLDER, linux.LINUX_FILENAME)
        #executable = os.path.join(TMP_PATH_FOLDER, 'chromedriver')
    return installation_file


@pytest.fixture
def tmp_folder():
    TMP_PATH_FOLDER = os.path.normpath(os.path.expanduser('~'))

    if sys.platform == 'win32':
        installation_file = os.path.join(TESTS_FOLDER, WIN_FILENAME)
        executable = os.path.join(TMP_PATH_FOLDER, 'chromedriver.exe')
    elif sys.platform == 'linux':
        installation_file = os.path.join(TESTS_FOLDER, linux.LINUX_FILENAME)
        executable = os.path.join(TMP_PATH_FOLDER, 'chromedriver')

    with ZipFile(installation_file) as z:
        z.extractall(TMP_PATH_FOLDER)
        z.close()

    if sys.platform == 'linux':
        st = os.stat(executable)
        os.chmod(executable, st.st_mode | stat.S_IEXEC)

    yield TMP_PATH_FOLDER
    clean_up(executable)

###############################################################################
# WINDOWS ESPECIFIC FUNCTIONS
###############################################################################


@pytest.mark.windows
def test_win_get_local_release(tmp_folder):
    release = get_local_release(tmp_folder)
    assert release == TEST_RELEASE


@pytest.mark.windows
def test_win_get_path_ok(tmp_folder):
    assert win_get_path() in (tmp_folder, APPVEYOR_PATH)


###############################################################################
# LINUX ESPECIFIC FUNCTIONS
###############################################################################

@pytest.mark.linux
@pytest.fixture(scope='session')
def tmp_local_driver(tmpdir_factory, installation_file):
    tmp_path = tmpdir_factory.getbasetemp()
    unzip(installation_file, path=tmp_path)

    executable = {'win32': 'chromedriver.exe', 'linux': 'chromedriver'}

    chromedriver = os.path.join(tmp_path, executable[sys.platform])
    st = os.stat(chromedriver)
    os.chmod(chromedriver, st.st_mode | stat.S_IEXEC)
    return tmp_path


@pytest.mark.linux
def test_linux_get_local_release(tmp_local_driver):
    release = linux.get_local_release(tmp_local_driver)
    assert release == TEST_RELEASE

@pytest.mark.linux
def test_linux_get_path(tmp_local_driver):
    assert os.path.dirname(linux_get_path()) == tmp_local_driver.strpath
    '''install chromedriver on tmp_dir and check if ok. Uninstall and
    then checj for raise'''
    pass

###############################################################################
# CHROMEGUARD - PLATFORM INDEPENDENT FUNCTIONS
###############################################################################

@pytest.mark.Guard
def test_guard_get_local_release(tmp_folder):
    g = Guard(path=tmp_folder)
    assert g.local_release == TEST_RELEASE


@pytest.mark.Guard
def test_guard_latest_release():
    g = Guard()
    assert g.latest_release == API_get_latest_release()


@pytest.mark.Guard
def test_guard_installation_filename():
    g = Guard()
    if sys.platform == 'win32':
        assert g.installation_file == WIN_FILENAME
    elif sys.platform == 'darwin':
        assert g.installation_file == MAC_FILENAME
    elif sys.platform == 'linux':
        assert g.installation_file == LINUX_FILENAME
    else:
        msg = 'Platform not supported - {}'.format(sys.platform)
        raise EnvironmentError(msg)


@pytest.mark.Guard
def test_guard_is_updated_false(tmp_folder):
    ''' The test installation refers to release 2.20. Should return False '''
    g = Guard(path=tmp_folder)
    assert g.is_updated is False


@pytest.mark.Guard
def test_guard_is_updated_true(tmp_folder):
    '''  Download the latest release, insert on path. Should return True '''

    g = Guard(path=tmp_folder)
    # download the latest release to the tmp path folder and unzi
    g.download()
    unzip(os.path.join(tmp_folder, g.installation_file), tmp_folder)
    assert g.is_updated is True


@pytest.mark.Guard
def test_guard_download_latest_release(tmp_folder):
    g = Guard(path=tmp_folder)
    g.download()
    assert os.path.isfile(os.path.join(tmp_folder, g.installation_file))


@pytest.mark.Guard
def test_guard_update_already_updated(tmp_folder):
    g = Guard(path=tmp_folder)
    # download the latest release to the tmp path folder and unzi
    g.download()
    unzip(os.path.join(tmp_folder, g.installation_file), tmp_folder)
    # already updated retunr None
    assert g.update() is None


@pytest.mark.Guard
def test_guard_update(tmp_folder):
    g = Guard(path=tmp_folder)
    g.update()
    assert g.local_release == g.latest_release


@pytest.mark.Guard
def test_guard_raise_for_update(tmp_folder):
    g = Guard(path=tmp_folder)
    with pytest.raises(NotUpdatedException):
        g.raise_for_update()
