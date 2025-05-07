# length for galios filed in crypto
# obviously this should be larger for production, but it takes really long 
# small bit size for testing
PRIME_BITS = 512
#pregenerated prime number, as running on separate clients leads to new params
# this should be changed, is only temporary workaround
DH_P = 36064510220814417136577321545666673304893267826047890995209117910441890556018907670988803198824213337627738610074372499484784089081637487906946490804949851 # A very large prime number (actual value would be much longer)
DH_G = 2  # Generator
