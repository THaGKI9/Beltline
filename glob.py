# flake8: noqa

# * Matches 0 or more characters in a single path portion
# ? Matches 1 character
# !pattern Matches anything that does not match any of the
# ** If a "globstar" is alone in a path portion, then it matches zero or more directories and subdirectories searching for matches. It does not crawl symlinked directories.
from os import path, sep, walk
from fnmatch import fnmatch


def iglob(pattern):
    filter_mode = False
    if pattern.startswith('!'):
        filter_mode = True
        pattern = pattern[1:]

    base, pat = split_pattern(pattern)

    if pat == '':
        # pattern with no magic is a specific path
        if path.exists(base) and not filter_mode:
            dirs, filename = path.split(base)
            yield base, filename

    else:
        for (dirpath, dirnames, filenames) in walk(base):
            rel_dirpath = path.relpath(dirpath, base)
            for filename in filenames:
                is_match = fnmatch(path.join(rel_dirpath, filename), pat)

                if (filter_mode and not is_match) \
                        or (not filter_mode and is_match):
                    yield (path.join(dirpath, filename),
                           path.join(rel_dirpath, filename))

    # return an empty generator function
    return
    yield


def glob(pattern):
    return list(iglob(pattern))


def has_magic(pattern):
    '''Check if the pattern contains character `*` or `?`'''
    magic_chars = {'*', '?', '[', '!'}
    for char in pattern:
        if char in magic_chars:
            return True
    return False


def split_pattern(pattern):
    paths = path.normpath(pattern).split(sep)
    base = '.'
    pat = ''
    is_found_base = False

    for p in paths:
        if is_found_base:
            pat = path.join(pat, p)

        elif has_magic(p):
            is_found_base = True
            pat = p

        else:
            base = path.join(base, p)

    return base, pat


if __name__ == '__main__':
    print(split_pattern('../asdf/../**/*/asd'))
    print(split_pattern('./asdfasd/asdfsad'))
    print(split_pattern('**/*'))
    print()
    glob_pat = '!../core/**/*.py'
    print('glob: ' + glob_pat)
    for i in glob(glob_pat):
        print(i)