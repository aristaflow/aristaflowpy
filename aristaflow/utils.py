# -*- coding: utf-8 -*-
import re
class Version(object):
    """ Parsing and comparing version strings
    """
    __pattern:re = re.compile("(\\d+)(?:\\.(\\d+))?(?:\\.(\\d+))?(?:\\.(\\d+))?(?:\\.(\\d+))?")
    
    def key(self, v:str) -> int:
        if not(v):
            return 0
        
        m:re = self.__pattern.match(v)
        # invalid version string
        if m == None:
            return 0
        
        gs = m.groups()
        key = 0;
        places = len(gs)
        for i in range(places):
            p = gs[i]
            if p == None:
                break
            if len(p) > 3:
                # ugh... unsupported
                return 0
            key += int(p) * 10**(places - i)

        #print(f"{v} = {key}")
        return key

VERSION = Version()

#print(v.compare("1.5.0", "1.5.0"))
#vs = ["999.999.999.999.999", "1.5.0", "2.3.555.0", "2.3.8", "5.1", "3", "0.9.6", "2.3.8.1", "2.3.5"]
#print(sorted(vs, key=v.key))
