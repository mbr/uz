import magic


def unravel(fn):
    with magic.Magic() as m:
        import pdb; pdb.set_trace()  # DEBUG-REMOVEME
        print m.id_filename(fn)
