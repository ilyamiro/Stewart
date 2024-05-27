

def subprocess(**kwargs):
    subprocess.run(
        kwargs["parameters"]["command"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


