import os
import sys
import argparse
import subprocess
import time
import threading
from bs4 import BeautifulSoup
import urllib.request

# TODO Add mirror flag
# TODO Add other wget flags
# TODO Cleanup handling of slashes
class ThreadedWget():
    def __init__(self, dl_url, output_dir, cutdirs=0, mirror=False, verbose=False, threads=15):

        self.win_clear_screen()

        if not os.path.isfile('wget.exe') and not os.path.isfile('util\wget.exe'):
            print('ERROR: Cannot locate wget.exe.  Ensure it exists in CWD or in util folder under CWD')
            sys.exit()

        self.download_url = dl_url
        self.cutdirs = cutdirs
        self.mirror = mirror
        self.verbose = False
        self.threads = int(threads)
        self.output_dir = output_dir

        print(os.getcwd())


    def run(self):
        """
        This method executes the actual download.  It calls the parse_remote_dir_tree method and waits for
        it to return.  Once it returns it waits until all download threads have finishes.  Prior to threads
        finishing it prints a list of the files currently being downloaded
        :return:
        """

        self.parse_remote_dir_tree(self.download_url, '')

        print('\nAll Download Threads Launched.\n')
        # TODO Make thread checking it's down method
        last_active = 0
        while threading.active_count() > 1:
            if last_active != threading.active_count():
                self.win_clear_screen()
                print('---------- ACTIVE DOWNLOAD THREADS ----------')
                print('The Following ', threading.active_count(), ' files are still downloading')
                for thrd in threading.enumerate():
                    print(thrd.name)
            last_active = threading.active_count()
            time.sleep(1)

        print('Success: All Downloads Have Finished')

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

        print('Path Before: ', path)
        print('Dir: ', dir)
        # TODO This is mega hackis.  Revisit this
        if path == '/':
            path = path + dir
        else:
            path = path + '/' + dir
        print('Path After: ', path)

        # TODO Cleanup Exception Handling
        try:
            response = urllib.request.urlopen(url)
        except:
            print('Failed to open URL: ', url)
            return

        parsed_page = BeautifulSoup(response)

        for link in parsed_page.find_all('a'):

            # Avoid climbing back to previous level
            if link.string == '[To Parent Directory]':
                if self.verbose:
                    print('Skipping parent directory')
                continue

            # Get file name and extension.  If folder ext will be None
            name, ext = os.path.splitext(link.string)

            if ext:
                files.append(link.string)
            else:
                dirs.append(link.string)

        for file in files:
            download_url = url + '/' + file

            # Manage the amount of concurrent downloads. Don't start more download threads until below threshold
            while threading.active_count() > self.threads:
                print('Max download threads reached.  Waiting for threads to decrease')
                time.sleep(0.5)

            # TODO This should not be hard coded
            #output_file = path.replace('/arma', '') + '/' + file
            output_file = '/' + file
            print('Output File: ', output_file)

            time.sleep(0.02)
            if self.verbose:
                print('Starting new thread with download_url as: ' + download_url)
                print('Starting new thread with output_file as: ' + output_file)

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
                url = url + '/'

            if self.verbose:
                print('Calling parse_remote_dir_tree with URL: ' + url + folder)

            self.parse_remote_dir_tree(url + folder, folder, path=path, previous=dir)

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

        wget_call = r'util\wget.exe %s --reject "index.html*" --quiet --mirror --no-parent ' \
                    r'--no-host-directories --cut-dirs=%s --directory-prefix=%s --output-file=download.txt' % (
                    download_url, self.cutdirs, self.output_dir)

        if self.verbose:
            print('Downloading File: ', output_file)

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
    parser.add_argument("output_dir", help="The directory to place the downloaded files")
    parser.add_argument("cutdirs", help="Passthrough for Wget's custdirs command line flag")
    parser.add_argument("threads", help="The number of download threads to run at once.")
    parser.add_argument("--verbose", action='store_true', help="Prints a more verbose output", default=False, dest="verbose")
    parser.add_argument("--mirror", action='store_true', help="Enable/Disable Wget's mirror functionality", default=False, dest="mirror")
    args = parser.parse_args()

    downloader = ThreadedWget(args.dl_url, args.output_dir, cutdirs=args.cutdirs, verbose=args.verbose,
                              threads=args.threads, mirror=args.mirror)
    downloader.run()


if __name__ == '__main__':
    main()