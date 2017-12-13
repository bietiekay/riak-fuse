#!/usr/bin/env python

# Quick test

import NameMapping

print(NameMapping.legacyPathToRiakBucketName('IMG_','/fdaf16c657d997656bbccc5752eefa9f/images/1620028670_192497.jpg'))
print(NameMapping.legacyPathToRiakBucketName('IMG_','/fdaf16c657d997656bbccc5752eefa9f/images/'))
print(NameMapping.legacyPathToRiakBucketName('IMG_','/fdaf16c657d997656bbccc5752eefa9f/images'))
print(NameMapping.legacyPathToRiakKeyName('/fdaf16c657d997656bbccc5752eefa9f/images/1620028670_192497.jpg'))
print(NameMapping.legacyPathToRiakKeyName('/fdaf16c657d997656bbccc5752eefa9f/imes/1620028670_192497.jpg'))
