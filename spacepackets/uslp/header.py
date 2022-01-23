

class UslpPrimaryHeader:
    """USLP transfer frame primary header with a length of 4 to 14 bytes. It constsits of 13
    fiedls position contiguously. For more information, refer to the USLP Blue Book CCSDS 732.1-B-2.
    p.77

    1. Transfer Frame Version Number or TFVN (4 bits)
    2. Spacecraft ID or SCID (16 bits)
    3. Source or destination identifier (1 bit)
    4. Virtual Channel ID or VCID (6 bits)
    5. Multiplexer Access Point or MAP ID (4 bits)
    6. End of Frame Primary Header (1 bit)
    7. Frame Length (16 bits)
    8. Bypass/Sequence Control Flag (1 bit)
    9. Protocol Control Command Flag (1 bit)
    10. Reserve Spares (2 bits)
    11. OCF flag (1 bit)
    12. VCF count length (3 bits)
    13. VCF count (0 to 56 bits)
    """
    def __init__(self):
        pass
