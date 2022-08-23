import lzma
import shutil
import tarfile
import time


def make_archive(folder_to_zip, path_lzma, delete_files=False):
    start_time = time.time()
    print("LZMA")
    print("     --- %s seconds ---" % (time.time() - start_time))
    xz_file = lzma.LZMAFile(path_lzma, mode="w")
    with tarfile.open(mode="w", fileobj=xz_file) as tar_xz_file:
        tar_xz_file.add(folder_to_zip)
    xz_file.close()

    print("LZMA create")
    print("     --- %s seconds ---" % (time.time() - start_time))

    if delete_files:
        shutil.rmtree(folder_to_zip)


def create_backup(global_var):
    from pathlib import Path

    dt = time.strftime("%Y_%m_%d__%H_%M_%S")

    try:
        bck_folder_path = global_var.bck_folder_path
    except:
        bck_folder_path = "./bck"

    try:
        base_name = global_var.base_name_private
    except:
        return False, None

    try:
        user_login = global_var.user_login
        if user_login != "":
            user_login = "%s_" % user_login
    except:
        user_login = ""

    Path(bck_folder_path).mkdir(parents=True, exist_ok=True)
    arch_search = bck_folder_path + user_login + "base_{}.tar.xz".format(dt)
    make_archive(base_name, arch_search)
    return True, arch_search
