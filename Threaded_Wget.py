import os
import sys
import argparse
import subprocess
import time
import threading
from bs4 import BeautifulSoup
import urllib.request
import urllib.error

# TODO Cleanup handling of slashes
# TODO If not output dir is use CWD
# TODO Add a queue for files to download.  This way while waiting on max threads the download list can continue to build


class ThreadedWget():

    def __init__(self, dl_url, output_dir, cutdirs=0, threads=15, mirror=False, verbose=False, no_parent=False,
                 no_host_directories=False):

        self.win_clear_screen()

        if not os.path.isfile('wget.exe') and not os.path.isfile('util\wget.exe'):
            print('ERROR: Cannot locate wget.exe.  Ensure it exists in CWD or in util folder under CWD')
            sys.exit()

        # Validate The Initial URL
        try:
            urllib.request.urlopen(dl_url)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print('[x] ERROR: Failed to open URL: ', dl_url)
            print('[x] Error Msg: ', e.reason)
            print('\n[x] Please Check URL And Try Again')
            time.sleep(5)
            sys.exit()

        if not output_dir:
            print('[!] No output directory given.  CWD will be used. ')
            response = input('[?] Do You Wish To Proceed? (y/n)')
            if response.lower() == 'n' or response.lower() == 'no':
                print('[!] Please use --output to specify output directory')
                time.sleep(4)
                sys.exit()
            else:
                self.output_dir = os.getcwd()
        else:
            self.output_dir = output_dir

        self.download_url = dl_url
        self.cutdirs = cutdirs
        self.verbose = verbose
        self.threads = int(threads)

        # Handle Wget Flags
        if not mirror:
            self.mirror = ''
        else:
            self.mirror = '--mirror'

        if not no_parent:
            self.no_parent = ''
        else:
            self.no_parent = '--no-parent'

        if not no_host_directories:
            self.no_host_directories = ''
        else:
            self.no_host_directories = '--no-host-directories'


    def run(self):
        """
        This method executes the actual download.  It calls the parse_remote_dir_tree method and waits for
        it to return.  Once it returns it waits until all download threads have finishes.  Prior to threads
        finishing it prints a list of the files currently being downloaded
        :return:
        """

        print('[+] Starting Parse And Download Of ' + self.download_url + '\n')

        self.parse_remote_dir_tree(self.download_url, '')

        print('\nAll Download Threads Launched.\n')
        # TODO Make thread checking it's down method
        last_active = 0
        while threading.active_count() > 1:
            if last_active != threading.active_count():
                self.win_clear_screen()
                print('---------- ACTIVE DOWNLOAD THREADS ----------')
                print('The Following ', threading.active_count() - 1, ' files are still downloading')
                for thrd in threading.enumerate():
                    if thrd.name.lower() == 'mainthread':
                        continue
                    print('[+] ', thrd.name)
            last_active = threading.active_count()
            time.sleep(1)

        print('[!] Success: All Downloads Have Finished')

    def parse_remote_dir_tree(self, url, dir, path='', previous=None):
        """
        Crawl a directory listing of a URL and find all files.  Pass each file off to a download function.
        Builds up seperate list of files and files on each directory level
        :param url: The URL to parse. Starts with base url and recursivly calls deeper URL
        :param dir: Current dir at time of calling function. Used to build of new URL
        :param path: Builds of the path of folders crawled into.  Used to build of URL
        :param previous:
        :return:
        """
        dirs = []
        files = []

        # Build up directory path
        # path = path + '/' + dir

        # TODO This is mega hackish.  Revisit
        if path == '/':
            path = path + dir
        else:
            path = path + '/' + dir

        # TODO Cleanup Exception Handling.  Will throw urllib.error.URLError if DNS lookup fails
        try:
            response = urllib.request.urlopen(url)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print('[x] ERROR: Failed to open URL: ', url)
            print('[x] Error Msg: ', e.reason)
            return

        parsed_page = BeautifulSoup(response)

        for link in parsed_page.find_all('a'):

            # Avoid climbing back to previous level
            if link.string == '[To Parent Directory]':
                if self.verbose:
                    print('[+] Skipping parent directory')
                continue

            # Get file name and extension.  If directory ext will be None
            name, ext = os.path.splitext(link.string)

            if ext:
                files.append(link.string)
            else:
                dirs.append(link.string)

        for file in files:
            download_url = url + '/' + file

            # Manage the amount of concurrent downloads. Don't start more download threads until below threshold
            while threading.active_count() > self.threads:
                print('[x] Max download threads reached.  Waiting for threads to decrease')
                time.sleep(2)

            output_file = '/' + file

            time.sleep(0.02)
            if self.verbose:
                print('[+] Starting new thread with download_url as: ' + download_url)
                print('[+] Starting new thread with output_file as: ' + output_file)

            t = threading.Thread(target=self._threaded_download, name=os.path.basename(output_file),
                                 args=(download_url, output_file,))
            t.start()

        for folder in dirs:
            # First entry can be blank. Skip Iteration
            if not folder:
                continue
            # TODO Don't think this check is needed. Verify. Remove from args if not needed
            if folder == previous:
                continue

            # TODO Hackish?
            # Add trailing slash
            if url[-1:] != '/':
                url += '/'

            if self.verbose:
                print('[+] Calling parse_remote_dir_tree with URL: ' + url + folder)

            next_url = url + folder

            self.parse_remote_dir_tree(next_url, folder, path=path, previous=dir)

    def _threaded_download(self, download_url, output_file):
        """
        Construct and call Wget to download individual files
        Wget is being used here as I cannot find a way to easily replicate Wget's mirror functionality via urllib
        :param download_url: The URL to download
        :param output_file: The file name and path of the local file
        :return: None
        """

        # Make sure output director if it does not exists
        if not os.path.exists(os.path.dirname(self.output_dir + output_file)):
            os.makedirs(os.path.dirname(self.output_dir + output_file))

        wget_call = r'util\wget.exe %s --reject "index.html*" --quiet %s %s ' \
                    r'%s --cut-dirs=%s --directory-prefix=%s --output-file=download.txt' % (
                    download_url, self.mirror, self.no_parent, self.no_host_directories, self.cutdirs, self.output_dir)

        if self.verbose:
            print('Downloading File: ', output_file)
            print(wget_call)

        # subprocess.DEVNULL is used to null output from Popen call
        run = subprocess.Popen(wget_call, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Block until process completes.  Otherwise thread exits while process still running
        run.communicate()
        if self.verbose:
            print('----- Thread Ending -----\n')


    def win_clear_screen(self):
        os.system('cls')


def main():
    parser = argparse.ArgumentParser(description="A wrapper for Windows Wget that will scan a whole http directory tree "
                                                 "and download all files. ")

    parser.add_argument("dl_url", help="This is the URL to download")
    #parser.add_argument("output_dir", help="The directory to place the downloaded files")
    parser.add_argument("--output", default=False, dest="output_dir")
    parser.add_argument("cutdirs", help="Passthrough for Wget's custdirs command line flag")
    parser.add_argument("--threads", default=15, dest="threads", help="The number of download threads to run at once.")
    parser.add_argument("--verbose", action='store_true', help="Prints a more verbose output", default=False, dest="verbose")
    parser.add_argument("--mirror", action='store_true', help="Enable/Disable Wget's mirror functionality", default=False, dest="mirror")
    parser.add_argument("--no_parent", action="store_true", default=False, dest="no_parent")
    parser.add_argument("--no_host_directories", action="store_true", default=False, dest="no_host_directories")
    args = parser.parse_args()


    downloader = ThreadedWget(args.dl_url, args.output_dir, cutdirs=args.cutdirs, threads=args.threads,
                              verbose=args.verbose, mirror=args.mirror, no_parent=args.no_parent,
                              no_host_directories=args.no_host_directories)
    try:
        downloader.run()
    except KeyboardInterrupt:
        print('[!] Keyboard Quit Detected')

if __name__ == '__main__':
    main()