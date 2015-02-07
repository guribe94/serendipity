//
//  CategoryInterfaceController.m
//  SerendipityTest
//
//  Created by Rahul Kapur on 2/6/15.
//  Copyright (c) 2015 Rahul Kapur. All rights reserved.
//

#import "CategoryInterfaceController.h"


@interface CategoryInterfaceController() {
    NSArray *labels;
    NSArray *contexts;
    
}


@property (strong, nonatomic) IBOutlet WKInterfaceButton *button;

@end


@implementation CategoryInterfaceController

- (void)awakeWithContext:(id)context {
    [super awakeWithContext:context];
    [self.button setTitle:(NSString *) context[0]];
    [self.button setBackgroundColor:context[1]];
    [self setTitle:@"Off"];
    
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
- (IBAction)tapButton {
    
    labels = [[NSArray alloc] initWithObjects:@"Restaurants", @"Bars", @"Deals", nil];
    contexts = [[NSArray alloc] initWithObjects:@"PlaceInterfaceController", @"PlaceInterfaceController", @"PlaceInterfaceController", nil];
    [self presentControllerWithNames:contexts contexts:labels];
    
}

@end



