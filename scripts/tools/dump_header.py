import json
import sys

def dump_header(path):
    with open(path, 'rb') as f:
        magic = f.read(4)
        if magic != b'\x12\x32\x34\x11':
            print(f"Invalid magic: {magic}")
            return
        
        json_len = int.from_bytes(f.read(4), byteorder='little')
        print(f"JSON Length: {json_len}")
        json_bytes = f.read(json_len)
        try:
            json_content = json_bytes.decode('utf-8')
        except UnicodeDecodeError:
            print("UTF-8 decode failed, trying latin-1")
            json_content = json_bytes.decode('latin-1')
            
        data = json.loads(json_content)
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    dump_header(sys.argv[1])
