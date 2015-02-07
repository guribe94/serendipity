//
//  InterfaceController.m
//  SerendipityTest WatchKit Extension
//
//  Created by Rahul Kapur on 2/5/15.
//  Copyright (c) 2015 Rahul Kapur. All rights reserved.
//

#import "InterfaceController.h"


@interface InterfaceController() {
    CGFloat increment;
    NSMutableArray *labels;
    NSMutableArray *contexts;
}

@property (strong, nonatomic) IBOutlet WKInterfaceButton *onButton;

@end


@implementation InterfaceController

- (void)awakeWithContext:(id)context {
    
    [super awakeWithContext:context];
    increment = 1.0;
    [self.onButton setAlpha:increment];
    [self.onButton setBackgroundColor:[UIColor greenColor]];
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
    
    NSMutableArray *restaurants = [[NSMutableArray alloc] initWithObjects:@"Restaurants", [UIColor greenColor], nil];
    NSMutableArray *bars = [[NSMutableArray alloc] initWithObjects:@"Bars", [UIColor orangeColor], nil];
    NSMutableArray *deals = [[NSMutableArray alloc] initWithObjects:@"Deals", [UIColor yellowColor], nil];
    
    labels = [[NSMutableArray alloc] initWithObjects:restaurants, bars, deals, nil];
    contexts = [[NSMutableArray alloc] initWithObjects:@"CategoryInterfaceController", @"CategoryInterfaceController", @"CategoryInterfaceController", nil];
    [self presentControllerWithNames:contexts contexts:labels];
    
    //[timer fire];
    /*NSArray *controllerNames = @[@"pageController", @"pageController", @"pageController", @"pageController", @"pageController"];
    NSArray *contexts = @[@"First", @"Second", @"Third", @"Fourth", @"Fifth"];
    [self presentControllerWithNames:controllerNames contexts:contexts]; */

    
    
    
}
/*-(void)updateUI {
    NSLog(@"hello");
    increment = increment + 0.1;
    [self.onButton setAlpha:increment];
    if (increment == 1.0) {
        [timer invalidate];
    }
    
    
} */

@end



