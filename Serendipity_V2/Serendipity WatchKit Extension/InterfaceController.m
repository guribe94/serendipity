//
//  InterfaceController.m
//  Serendipity WatchKit Extension
//
//  Created by Rahul Kapur on 2/7/15.
//  Copyright (c) 2015 Rahul Kapur. All rights reserved.
//

#import "InterfaceController.h"



@interface InterfaceController() {
    NSMutableArray * mainArray;
    NSMutableArray * names;
    NSMutableArray *milanos;
    NSMutableArray *amigos;
    NSMutableArray *diginn;
}

@property (strong, nonatomic) IBOutlet WKInterfaceButton *onOffButton;


@end


@implementation InterfaceController

- (void)awakeWithContext:(id)context {
    
    
    [super awakeWithContext:context];
    
    
}

- (void)willActivate {
    // This method is called when watch view controller is about to be visible to user
    [super willActivate];
}

- (void)didDeactivate {
    // This method is called when watch view controller is no longer visible
    [super didDeactivate];
}
- (IBAction)buttonTapped {
    [self.onOffButton setTitle:@"On"];
    [self.onOffButton setBackgroundColor:[UIColor greenColor]];
    milanos = [[NSMutableArray alloc] initWithObjects:@"Restaurants", [UIColor blueColor], @"milanos", @"3.5 Stars", @"1 mile", nil];
    
    amigos = [[NSMutableArray alloc] initWithObjects:@"Bars", [UIColor orangeColor], @"amigos", @"4 Stars", @"1 mile", nil];
    diginn = [[NSMutableArray alloc] initWithObjects:@"Theaters", [UIColor greenColor], @"diginn", @"4 Stars", @"1 mile", nil];
    mainArray = [[NSMutableArray alloc] initWithObjects:milanos,amigos,diginn, nil];
    names = [[NSMutableArray alloc] initWithObjects: @"ItemInterfaceController", @"ItemInterfaceController", @"ItemInterfaceController", nil];
    
    [self presentControllerWithNames:names contexts:mainArray];
    
}

@end



