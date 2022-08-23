import argparse


def get_params():
    parser = argparse.ArgumentParser()
    parser.add_argument("-mode", type=str,
                        help="bot mode")

    parser.add_argument("-cfg", type=str,
                        help="Path to cfg file")

    parser.add_argument("-debug", type=str,
                        help="debug mode")

    parser.add_argument("-day_count", type=int,
                        help="display a square of a given number")

    parser.add_argument("-v", "--verbose", action="store_true",
                        help="increase output verbosity")

    args = parser.parse_args()

    return args
