#import <Foundation/Foundation.h>
#import <Vision/Vision.h>
#import <AppKit/AppKit.h>
#import <ImageIO/ImageIO.h>

NSArray* runOCRWithOrientation(CGImageRef cgImage, CGImagePropertyOrientation orientation, VNRequestTextRecognitionLevel level, NSArray<NSString*>* langs) {
    NSMutableArray *lines = [NSMutableArray array];
    VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] initWithCompletionHandler:^(VNRequest * _Nonnull req, NSError * _Nullable error) {
        for (VNRecognizedTextObservation *obs in req.results) {
            VNRecognizedText *top = [[obs topCandidates:1] firstObject];
            if (top) {
                CGRect box = obs.boundingBox;
                [lines addObject:@{
                    @"text": top.string,
                    @"y": @(box.origin.y),
                    @"x": @(box.origin.x),
                    @"h": @(box.size.height),
                    @"w": @(box.size.width)
                }];
            }
        }
    }];
    request.recognitionLevel = level;
    request.recognitionLanguages = langs;
    request.usesLanguageCorrection = YES;

    VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:cgImage orientation:orientation options:@{}];
    NSError *err = nil;
    [handler performRequests:@[request] error:&err];
    return lines;
}

NSUInteger horizontalTextScore(NSArray *lines) {
    NSUInteger score = 0;
    for (NSDictionary *item in lines) {
        NSString *t = item[@"text"];
        double w = [item[@"w"] doubleValue];
        double h = [item[@"h"] doubleValue];
        if (t && [t length] > 0) {
            if (w >= h) {
                score += [t length] * 3;
            } else {
                score += [t length];
            }
        }
    }
    return score;
}

NSDictionary* runBestOrientationOCR(CGImageRef cgImage, VNRequestTextRecognitionLevel level, NSArray<NSString*>* langs) {
    NSArray *upLines = runOCRWithOrientation(cgImage, kCGImagePropertyOrientationUp, level, langs);
    NSArray *rightLines = runOCRWithOrientation(cgImage, kCGImagePropertyOrientationRight, level, langs);
    NSArray *leftLines = runOCRWithOrientation(cgImage, kCGImagePropertyOrientationLeft, level, langs);

    NSArray *best = upLines;
    NSString *bestOrient = @"up";
    NSUInteger bestScore = horizontalTextScore(upLines);

    NSUInteger rightScore = horizontalTextScore(rightLines);
    if (rightScore > bestScore) {
        best = rightLines;
        bestOrient = @"right";
        bestScore = rightScore;
    }

    NSUInteger leftScore = horizontalTextScore(leftLines);
    if (leftScore > bestScore) {
        best = leftLines;
        bestOrient = @"left";
        bestScore = leftScore;
    }

    return @{@"lines": best, @"orientation": bestOrient};
}

NSArray* detectQRCodes(CGImageRef cgImage) {
    NSMutableArray *codes = [NSMutableArray array];
    VNDetectBarcodesRequest *req = [[VNDetectBarcodesRequest alloc] initWithCompletionHandler:^(VNRequest * _Nonnull request, NSError * _Nullable error) {
        for (VNBarcodeObservation *obs in request.results) {
            if (obs.payloadStringValue) {
                CGRect box = obs.boundingBox;
                [codes addObject:@{
                    @"payload": obs.payloadStringValue,
                    @"x": @(box.origin.x),
                    @"y": @(box.origin.y),
                    @"w": @(box.size.width),
                    @"h": @(box.size.height)
                }];
            }
        }
    }];
    VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:cgImage options:@{}];
    NSError *err = nil;
    [handler performRequests:@[req] error:&err];
    return codes;
}

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        if (argc < 2) {
            printf("{\"error\": \"Missing file path\"}\n");
            return 1;
        }
        NSString *path = [NSString stringWithUTF8String:argv[1]];
        NSURL *url = [NSURL fileURLWithPath:path];
        NSImage *image = [[NSImage alloc] initWithContentsOfURL:url];
        if (!image) {
            printf("{\"error\": \"Failed to load image\"}\n");
            return 1;
        }
        CGImageRef cgImage = [image CGImageForProposedRect:NULL context:nil hints:nil];
        if (!cgImage) {
            printf("{\"error\": \"Failed to get CGImage\"}\n");
            return 1;
        }

        NSArray *langs = @[@"zh-Hant", @"zh-Hans", @"ja-JP", @"en-US"];
        NSDictionary *res = runBestOrientationOCR(cgImage, VNRequestTextRecognitionLevelAccurate, langs);
        NSArray *lines = res[@"lines"];
        NSString *orientation = res[@"orientation"];
        NSString *mode = @"accurate";
        if ([lines count] == 0) {
            res = runBestOrientationOCR(cgImage, VNRequestTextRecognitionLevelFast, @[@"en-US"]);
            lines = res[@"lines"];
            orientation = res[@"orientation"];
            mode = @"fast";
        }
        NSArray *qrcodes = detectQRCodes(cgImage);

        NSData *jsonData = [NSJSONSerialization dataWithJSONObject:@{
            @"mode": mode,
            @"orientation": orientation ?: @"up",
            @"lines": lines ?: @[],
            @"qrcodes": qrcodes ?: @[]
        } options:0 error:nil];
        NSString *jsonStr = [[NSString alloc] initWithData:jsonData encoding:NSUTF8StringEncoding];
        printf("%s\n", [jsonStr UTF8String]);
    }
    return 0;
}
