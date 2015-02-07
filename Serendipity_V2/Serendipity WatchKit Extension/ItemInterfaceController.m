//
//  ItemInterfaceController.m
//  Serendipity
//
//  Created by Rahul Kapur on 2/7/15.
//  Copyright (c) 2015 Rahul Kapur. All rights reserved.
//

#import "ItemInterfaceController.h"


@interface ItemInterfaceController()
@property (strong, nonatomic) IBOutlet WKInterfaceButton *nameLabel;
@property (strong, nonatomic) IBOutlet WKInterfaceButton *ratingLabel;
@property (strong, nonatomic) IBOutlet WKInterfaceButton *directionsButton;
@property (strong, nonatomic) IBOutlet WKInterfaceButton *dealsButton;
@property (strong, nonatomic) IBOutlet WKInterfaceLabel *categoriesLabel;
@property (strong, nonatomic) IBOutlet WKInterfaceGroup *group;

@end


@implementation ItemInterfaceController

- (void)awakeWithContext:(id)context {
    [super awakeWithContext:context];
    [self.categoriesLabel setText:(NSString *)context[0]];
    [self.group setBackgroundColor:context[1]];
    [self.nameLabel setTitle:context[2]];
    [self.ratingLabel setTitle:context[3]];
    [self.directionsButton setTitle:context[4]];
    
    
    
    // Configure interface objects here.
}

- (void)willActivate {
    // This method is called when watch view controller is about to be visible to user
    [super willActivate];
}

- (void)didDeactivate {
    // This method is called when watch view controller is no longer visible
    [super didDeactivate];
}

@end



