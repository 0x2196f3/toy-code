def xor_encrypt_decrypt(data: bytes, password: str) -> bytes:
    result = bytearray()
    
    for i in range(len(data)):
        result.append(data[i] ^ ord(password[i % len(password)]))
    
    return bytes(result)

def main(src_file_path: str, dst_file_path: str, password: str):
    with open(src_file_path, 'rb') as src_file:
        data = src_file.read()
    
    encrypted_decrypted_data = xor_encrypt_decrypt(data, password)
    
    with open(dst_file_path, 'wb') as dst_file:
        dst_file.write(encrypted_decrypted_data)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 4:
        print("Usage: python script.py <src_file_path> <dst_file_path> <password>")
        sys.exit(1)
    
    src_file_path = sys.argv[1]
    dst_file_path = sys.argv[2]
    password = sys.argv[3]
    
    main(src_file_path, dst_file_path, password)
